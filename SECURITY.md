# Security policy

## Supported versions

Security fixes are made on the latest released minor version. Older releases and
unreleased forks are not supported.

## Report a vulnerability

Do not open a public issue. Use this repository's **Security > Advisories > Report
a vulnerability** flow to send a private GitHub Security Advisory. Include the
affected version, impact, reproduction, and any suggested mitigation. Remove real
delivery data, credentials, and personal information from the report.

Maintainers will acknowledge the report when it is triaged, coordinate remediation
and disclosure through the advisory, and credit the reporter if requested. No fixed
response deadline is promised by this volunteer-maintained project.

## Scope

The packaged skill is intentionally local and dependency-free: it contains no
network calls, telemetry, credential handling, MCP server, or package installation.
Reports about malicious CSV formulas in a user's original spreadsheet application,
model-provider data retention, host sandbox policy, or third-party AI clients belong
to those products unless this repository's code causes the exposure.
