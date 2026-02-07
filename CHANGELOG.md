# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Open-source governance documentation (`CONTRIBUTING`, `SECURITY`, `SUPPORT`, `CODE_OF_CONDUCT`, `CODEOWNERS`)
- CI/CD workflows for automated checks and container publishing
- SDK smoke trace check script for integration validation
- Governance and operations docs (`GOVERNANCE`, `MAINTAINERS`, `RELEASE`, `docs/ARCHITECTURE`, `docs/OPERATIONS`, `docs/TROUBLESHOOTING`)

### Changed
- Dashboard now distinguishes loading, empty, and error states for trace fetch failures
- UI iconography migrated from emoji to icon components in dashboard components
- README documentation index and troubleshooting guidance were expanded

### Fixed
- SDK tracer context consistency for decorator-based instrumentation
- Removed local absolute paths from contributor/support docs
