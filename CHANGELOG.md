# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Open-source governance documentation (`CONTRIBUTING`, `SECURITY`, `SUPPORT`, `CODE_OF_CONDUCT`, `CODEOWNERS`)
- CI/CD workflows for automated checks and container publishing
- SDK smoke trace check script for integration validation
- Governance and operations docs (`GOVERNANCE`, `MAINTAINERS`, `RELEASE`, `docs/ARCHITECTURE`, `docs/OPERATIONS`, `docs/TROUBLESHOOTING`)
- Dependabot configuration for Actions/npm/pip/docker updates
- CodeQL scanning workflow and tag-based release workflow
- Backend, SDK, and frontend test suites with CI execution

### Changed
- Dashboard now distinguishes loading, empty, and error states for trace fetch failures
- UI iconography migrated from emoji to icon components in dashboard components
- README documentation index and troubleshooting guidance were expanded
- CI now runs additional security checks and labels failed PRs instead of auto-closing
- Dockerfiles hardened to run as non-root users

### Fixed
- SDK tracer context consistency for decorator-based instrumentation
- Removed local absolute paths from contributor/support docs
- SDK package metadata now points to the correct repository and maintainer contacts
