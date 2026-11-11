#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("ssm_runtime.py")
SPEC = importlib.util.spec_from_file_location("ssm_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SharedRuntimeTests(unittest.TestCase):
    def test_repository_root_and_assets_are_inside_repository(self):
        self.assertEqual(MODULE.REPOSITORY_ROOT.name, "vul-harness")
        for path in MODULE.asset_paths("lab-c"):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(str(path).startswith(str(MODULE.REPOSITORY_ROOT)))

    def test_bootstrap_commands_use_integrity_checks_and_ssm_safe_loopback_layout(self):
        commands = MODULE.build_commands("lab-d", "base")
        joined = "\n".join(commands)
        self.assertIn("sha256sum", joined)
        self.assertIn(MODULE.COMPOSE_VERSION, joined)
        self.assertIn("docker compose", joined)
        self.assertIn("/opt/vulharness/scenarios/php2shell", joined)
        self.assertNotIn("ssh ", joined)
        self.assertNotIn("0.0.0.0:8080", joined)

    def test_remediation_transfers_the_lab_d_update_override(self):
        joined = "\n".join(MODULE.build_commands("lab-d", "remediate"))
        self.assertIn("compose.lab-d.update.yaml", joined)
        self.assertIn("docker compose -f '/opt/vulharness/scenarios/php2shell/labs/aws/lab-d/compose.lab-d.yaml' -f", joined)


if __name__ == "__main__":
    unittest.main()
