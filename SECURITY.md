# Security Policy

## Supported Versions

The latest `main` branch and latest release are considered supported.

## Reporting a Vulnerability

Please report vulnerabilities privately.

- Preferred: open a private GitHub security advisory from the repository
  `Security` tab (`Advisories` -> `Report a vulnerability`).
- If advisory submission is unavailable, contact maintainers through private channels listed in [MAINTAINERS.md](MAINTAINERS.md).
- Include:
  - affected component(s)
  - impact summary
  - reproduction steps or PoC
  - suggested remediation (if known)

Do **not** disclose vulnerabilities publicly until a fix is available.

## Response Targets

- Initial acknowledgment: within 3 business days
- Triage and severity assignment: within 7 business days
- Fix timeline: depends on severity and complexity

## Disclosure Process

1. Confirm and triage the report.
2. Prepare and test a fix.
3. Coordinate disclosure timeline with reporter.
4. Publish advisory and patched release.

## Scope Guidance

- This policy covers code in `backend/`, `frontend/`, `sdk/`, and CI workflows in `.github/workflows/`.
- Dependency vulnerabilities should include package name, version, and advisory reference where possible.
