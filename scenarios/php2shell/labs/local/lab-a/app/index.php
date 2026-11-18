<?php

declare(strict_types=1);

const FIXED_UPSTREAM_RELEASES = [
    'CVE-2026-109618' => [
        '8.2' => '8.2.35',
        '8.3' => '8.3.36',
        '8.4' => '8.4.27',
        '8.5' => '8.5.12',
    ],
    'CVE-2026-109619' => [
        '8.2' => '8.2.35',
        '8.3' => '8.3.36',
        '8.4' => '8.4.27',
        '8.5' => '8.5.12',
    ],
];

const ADVISORY_URLS = [
    'CVE-2026-109618' => 'https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w',
    'CVE-2026-109619' => 'https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp',
];

function escapeValue(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function iniValue(string $name): string
{
    $value = ini_get($name);

    if ($value === false || $value === '') {
        return 'not reported';
    }

    return (string) $value;
}

function enabledValue(string $name): string
{
    $value = ini_get($name);

    if ($value === false || $value === '') {
        return 'disabled or not reported';
    }

    return filter_var($value, FILTER_VALIDATE_BOOLEAN) ? 'enabled' : 'disabled';
}

/**
 * This is an upstream-version signal only. It does not assess package
 * backports, deployment conditions, applicability, or exposure.
 *
 * @return array{label: string, detail: string}
 */
function upstreamVersionAssessment(string $version, string $cve): array
{
    if (!isset(FIXED_UPSTREAM_RELEASES[$cve])) {
        return [
            'label' => 'Unknown / requires further investigation',
            'detail' => 'No advisory threshold is configured for this identifier.',
        ];
    }

    if (!preg_match('/^(\d+\.\d+)/', $version, $matches)) {
        return [
            'label' => 'Unknown / requires further investigation',
            'detail' => 'The runtime version could not be mapped to an advisory branch.',
        ];
    }

    $branch = $matches[1];
    $fixedRelease = FIXED_UPSTREAM_RELEASES[$cve][$branch] ?? null;

    if ($fixedRelease === null) {
        return [
            'label' => 'Unknown / requires further investigation',
            'detail' => 'The observed branch is outside the explicitly documented fixed-release mapping; verify vendor guidance and advisory applicability.',
        ];
    }

    if (version_compare($version, $fixedRelease, '>=')) {
        return [
            'label' => 'Fixed upstream version',
            'detail' => "Observed {$version} is at or above the upstream {$fixedRelease} threshold for this branch.",
        ];
    }

    return [
        'label' => 'Potentially affected upstream version',
        'detail' => "Observed {$version} is below the upstream {$fixedRelease} threshold; package backports and applicability require further investigation.",
    ];
}

$inspect = isset($_GET['inspect']) && $_GET['inspect'] === '1';
$jsonFormat = isset($_GET['format']) && $_GET['format'] === 'json';
$phpVersion = PHP_VERSION;
$sapi = php_sapi_name();
$observedAt = gmdate(DATE_ATOM);

if ($inspect && $jsonFormat) {
    http_response_code(200);
    header('Content-Type: application/json; charset=UTF-8');
    header('Cache-Control: no-store');
    header('X-Content-Type-Options: nosniff');

    echo json_encode([
        'schema_version' => 1,
        'php_version' => $phpVersion,
        'sapi' => $sapi,
        'observed_at' => $observedAt,
    ], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    exit;
}

$assessments = [];

foreach (ADVISORY_URLS as $cve => $advisoryUrl) {
    $assessments[$cve] = [
        'url' => $advisoryUrl,
        ...upstreamVersionAssessment($phpVersion, $cve),
    ];
}

$runtime = [
    'PHP version' => $phpVersion,
    'Server API / SAPI' => $sapi,
    'Loaded PHP configuration file' => php_ini_loaded_file() ?: 'not reported',
    'Memory limit' => iniValue('memory_limit'),
    'File uploads' => enabledValue('file_uploads'),
    'Session upload progress' => enabledValue('session.upload_progress.enabled'),
    'UTC observation timestamp' => $observedAt,
];

?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>VulHarness — PHP2Shell Local Investigation</title>
    <style>
        :root {
            color-scheme: light;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.5;
            color: #1f2937;
            background: #f3f4f6;
        }
        body { margin: 0; }
        main { max-width: 920px; margin: 0 auto; padding: 2rem 1rem 3rem; }
        .site-header { align-items: center; display: flex; justify-content: space-between; gap: 1rem; padding: 0.25rem 0 1.5rem; }
        .brand { color: #111827; }
        .brand-project { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; }
        .brand-tagline { color: #374151; font-size: 0.98rem; margin-top: 0.1rem; }
        .brand-attribution { color: #6b7280; font-size: 0.82rem; margin-top: 0.15rem; }
        .card { background: #fff; border: 1px solid #d1d5db; border-radius: 0.75rem; padding: 1.25rem; margin-top: 1rem; box-shadow: 0 4px 16px rgb(15 23 42 / 0.06); }
        h1, h2 { line-height: 1.2; }
        h1 { margin-top: 0; }
        h2 { font-size: 1.25rem; }
        button, .button { border-radius: 0.4rem; cursor: pointer; display: inline-block; font: inherit; padding: 0.65rem 0.9rem; text-decoration: none; }
        button { background: #1d4ed8; border: 0; color: #fff; }
        button:hover { background: #1e40af; }
        .button-secondary { background: #fff; border: 1px solid #6b7280; color: #1f2937; }
        .button-secondary:hover { background: #f3f4f6; border-color: #374151; }
        .actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1rem; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border-bottom: 1px solid #e5e7eb; padding: 0.6rem 0.4rem; text-align: left; vertical-align: top; }
        th { width: 34%; }
        .notice { background: #eff6ff; border-left: 0.3rem solid #2563eb; padding: 0.75rem 1rem; }
        .assessment { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 0.5rem; margin-top: 0.75rem; padding: 0.75rem; }
        .label { font-weight: 700; }
        code { background: #f3f4f6; border-radius: 0.25rem; padding: 0.1rem 0.25rem; }
        a { color: #1d4ed8; }
        a:focus-visible, button:focus-visible { outline: 3px solid #f59e0b; outline-offset: 3px; }
        .site-footer { border-top: 1px solid #d1d5db; color: #4b5563; display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; justify-content: space-between; margin-top: 2rem; padding-top: 1rem; }
        .site-footer p { margin: 0; }
        .site-footer nav { display: flex; flex-wrap: wrap; gap: 1rem; }
        @media (max-width: 600px) {
            .site-footer { align-items: flex-start; flex-direction: column; }
        }
    </style>
</head>
<body>
<main>
    <header class="site-header">
        <div class="brand" aria-label="VulHarness by AI Security Lab">
            <div class="brand-project">VulHarness</div>
            <div class="brand-tagline">Investigate vulnerabilities. Verify findings.</div>
            <div class="brand-attribution">By AI Security Lab</div>
        </div>
    </header>

    <section class="card">
        <h1>PHP2Shell Local Investigation</h1>
        <p>Hello World! This PHP application is running.</p>
        <p>Use the button to inspect the runtime serving this HTTP request. The displayed advisory status is an upstream-version signal only.</p>
        <form method="get" class="actions">
            <button type="submit" name="inspect" value="1">Inspect Runtime</button>
<?php if ($inspect): ?>
            <a class="button button-secondary" href="/">Reset Test</a>
<?php endif; ?>
        </form>
    </section>

<?php if ($inspect): ?>
    <section class="card">
        <h2>Observed runtime evidence</h2>
        <table>
            <tbody>
            <?php foreach ($runtime as $label => $value): ?>
                <tr>
                    <th scope="row"><?= escapeValue($label) ?></th>
                    <td><code><?= escapeValue($value) ?></code></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </section>

    <section class="card">
        <h2>Upstream version-based advisory assessment</h2>
        <p class="notice">These labels compare the observed PHP version with documented upstream thresholds. They do not assess distribution backports, applicable conditions, or demonstrated exposure.</p>
        <?php foreach ($assessments as $cve => $assessment): ?>
            <div class="assessment">
                <p><span class="label"><?= escapeValue($cve) ?>:</span> <?= escapeValue($assessment['label']) ?></p>
                <p><?= escapeValue($assessment['detail']) ?></p>
                <p><a href="<?= escapeValue($assessment['url']) ?>">Read the official PHP advisory</a></p>
            </div>
        <?php endforeach; ?>
    </section>

    <section class="card">
        <h2>Application exposure</h2>
        <p class="notice"><span class="label">Application exposure: Not independently verified</span></p>
        <p>Actual applicability depends on the serving runtime, effective configuration, deployment and worker conditions, request paths, application behavior, and vendor patch status. Runtime inspection alone does not prove vulnerability or exploitability.</p>
    </section>
<?php endif; ?>

    <footer class="site-footer">
        <p><strong>VulHarness · Built by AI Security Lab</strong></p>
        <nav aria-label="Project links">
            <a href="https://www.aisecuritylab.com">AI Security Lab</a>
            <a href="https://github.com/The-AI-Security-Lab/vul-harness">GitHub</a>
        </nav>
    </footer>
</main>
</body>
</html>
