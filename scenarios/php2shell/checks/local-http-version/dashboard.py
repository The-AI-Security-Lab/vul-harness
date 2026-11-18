#!/usr/bin/env python3
"""Local-only VulHarness runtime inventory using the shared checker."""

from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Sequence

from checker import (
    CheckReport,
    EXPLOITABILITY_STATEMENT,
    FIXED,
    INCONCLUSIVE,
    POTENTIALLY_AFFECTED,
    TargetConfig,
    load_targets,
    run_checks,
    summary_result,
)


DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8081
MAX_REQUEST_BODY_BYTES = 1_024


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _remediation_note(status: str) -> str:
    if status == POTENTIALLY_AFFECTED:
        return (
            "Follow the approved remediation workflow, redeploy, then independently "
            "recheck the serving runtime."
        )
    if status == FIXED:
        return "No version-threshold remediation is indicated by this observation."
    return "Resolve missing or inconclusive evidence before making a remediation decision."


def _details(report: Optional[CheckReport]) -> str:
    if report is None:
        return "<p>No runtime evidence has been collected in this dashboard session.</p>"
    assessments = "".join(
        f"<li><strong>{_text(item.cve)}:</strong> {_text(item.result)} — "
        f"{_text(item.reason)}</li>"
        for item in report.assessments
    )
    error = ""
    if report.error_code:
        error = (
            f'<p class="error"><strong>Evidence error:</strong> '
            f"{_text(report.error_code)} — {_text(report.error_message or '')}</p>"
        )
    return f"""
        {error}
        <dl>
            <dt>SAPI</dt><dd>{_text(report.sapi or 'unavailable')}</dd>
            <dt>Evidence source</dt><dd>{_text(report.target.endpoint)}</dd>
        </dl>
        <ul>{assessments}</ul>
        <p><strong>Limitation:</strong> {_text(EXPLOITABILITY_STATEMENT)}</p>
    """


def _runtime_row(target: TargetConfig, report: Optional[CheckReport]) -> str:
    status = summary_result(report) if report is not None else INCONCLUSIVE
    version = report.php_version if report is not None else None
    observed_at = report.observed_at if report is not None else None
    return f"""
        <tr>
            <td><strong>{_text(target.identifier)}</strong></td>
            <td class="endpoint">{_text(target.endpoint)}</td>
            <td>{_text(version or 'not checked')}</td>
            <td><span class="status {_text(status)}">{_text(status if report else 'not checked')}</span></td>
            <td>{_text(observed_at or 'not checked')}</td>
            <td>
                <button class="disabled-action" type="button" disabled aria-disabled="true">Remediate</button>
                <div class="action-note">{_text(_remediation_note(status))}</div>
            </td>
        </tr>
        <tr class="details-row">
            <td colspan="6">
                <details>
                    <summary>Evidence details for {_text(target.identifier)}</summary>
                    {_details(report)}
                </details>
            </td>
        </tr>
    """


def render_page(
    targets: Sequence[TargetConfig],
    reports: Optional[Sequence[CheckReport]] = None,
) -> str:
    report_by_id = (
        {} if reports is None else {report.target.identifier: report for report in reports}
    )
    rows = "".join(
        _runtime_row(target, report_by_id.get(target.identifier)) for target in targets
    )
    empty_state = (
        '<p class="empty-state">No observations yet. Select <strong>Check Runtimes</strong> '
        "to collect fresh, read-only evidence from every configured target.</p>"
        if reports is None
        else ""
    )
    button_label = "Check Runtimes" if reports is None else "Recheck"

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VulHarness — Runtime Inventory</title>
    <style>
        :root {{ color-scheme: light; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1f2937; background: #f3f4f6; line-height: 1.5; }}
        body {{ margin: 0; }}
        main {{ max-width: 1180px; margin: 0 auto; padding: 2rem 1rem 3rem; }}
        header {{ margin-bottom: 1.5rem; }}
        .brand {{ color: #111827; font-size: 1.5rem; font-weight: 800; }}
        .tagline {{ color: #374151; }}
        .attribution {{ color: #6b7280; font-size: 0.85rem; }}
        .badge {{ color: #1d4ed8; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}
        .card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 0.75rem; box-shadow: 0 4px 16px rgb(15 23 42 / 0.06); margin-top: 1rem; padding: 1.25rem; }}
        h1, h2 {{ line-height: 1.2; }}
        h1 {{ margin-top: 0.25rem; }}
        button {{ background: #1d4ed8; border: 0; border-radius: 0.4rem; color: #fff; cursor: pointer; font: inherit; padding: 0.7rem 1rem; }}
        button:hover {{ background: #1e40af; }}
        button:focus-visible {{ outline: 3px solid #f59e0b; outline-offset: 3px; }}
        .disabled-action, .disabled-action:hover {{ background: #d1d5db; color: #6b7280; cursor: not-allowed; }}
        .action-note {{ color: #4b5563; font-size: 0.8rem; margin-top: 0.4rem; min-width: 190px; }}
        .table-wrap {{ overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border-bottom: 1px solid #e5e7eb; padding: 0.75rem; text-align: left; vertical-align: top; }}
        th {{ background: #f9fafb; font-size: 0.85rem; }}
        .endpoint {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }}
        .details-row td {{ background: #f9fafb; padding-top: 0.45rem; }}
        details {{ max-width: 920px; }}
        summary {{ cursor: pointer; font-weight: 700; }}
        dl {{ display: grid; grid-template-columns: 140px 1fr; gap: 0.35rem 1rem; }}
        dt {{ font-weight: 700; }}
        dd {{ margin: 0; overflow-wrap: anywhere; }}
        .status {{ border-radius: 999px; display: inline-block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.5rem; overflow-wrap: anywhere; }}
        .fixed_upstream_version {{ background: #dcfce7; color: #166534; }}
        .potentially_affected_upstream_version {{ background: #ffedd5; color: #9a3412; }}
        .inconclusive {{ background: #e5e7eb; color: #374151; }}
        .error {{ background: #fef2f2; border-left: 0.35rem solid #b91c1c; padding: 0.75rem; }}
        .empty-state {{ background: #eff6ff; border-left: 0.35rem solid #2563eb; padding: 0.75rem; }}
        footer {{ border-top: 1px solid #d1d5db; color: #4b5563; margin-top: 2rem; padding-top: 1rem; }}
        @media (max-width: 640px) {{ dl {{ grid-template-columns: 1fr; }} main {{ padding: 1rem 0.5rem 2rem; }} }}
    </style>
</head>
<body>
<main>
    <header>
        <div class="brand">VulHarness</div>
        <div class="tagline">Investigate vulnerabilities. Verify findings.</div>
        <div class="attribution">By AI Security Lab</div>
    </header>
    <section class="card">
        <div class="badge">Hello World 2.0</div>
        <h1>Discovered PHP Runtimes</h1>
        <p>This inventory checks the explicit local target registry. It is not host-wide discovery and accepts no URL or command input.</p>
        <form method="post" action="/check">
            <button type="submit">{_text(button_label)}</button>
        </form>
        {empty_state}
    </section>
    <section class="card">
        <h2>Configured runtime inventory</h2>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Runtime ID</th><th>Endpoint</th><th>Observed PHP version</th><th>Assessment status</th><th>Last observation</th><th>Action</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </section>
    <footer><strong>VulHarness · Built by AI Security Lab</strong></footer>
</main>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "VulHarnessDashboard/2"
    targets: tuple[TargetConfig, ...] = ()

    def _write_html(self, status: int, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self.send_error(404)
            return
        self._write_html(200, render_page(self.targets))

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/check":
            self.send_error(404)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if content_length < 0 or content_length > MAX_REQUEST_BODY_BYTES:
            self.send_error(413)
            return
        if content_length:
            self.rfile.read(content_length)
        self._write_html(200, render_page(self.targets, run_checks(self.targets)))

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    DashboardHandler.targets = load_targets()
    server = ThreadingHTTPServer((DASHBOARD_HOST, DASHBOARD_PORT), DashboardHandler)
    server.daemon_threads = True
    print(f"VulHarness runtime inventory: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print("Press Ctrl+C to stop the dashboard.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
