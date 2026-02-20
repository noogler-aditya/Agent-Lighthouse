# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/) and this project follows [Semantic Versioning](https://semver.org/).

## [0.4.0] — 2026-02-20

### Added
- **CLI**: `agent-lighthouse init` for zero-config onboarding (interactive login + `.env` setup)
- **CLI**: `agent-lighthouse status` to check backend health and auth
- **CLI**: `agent-lighthouse traces --last N` to list recent traces from terminal
- **CLI**: `al` short alias for all commands
- **CLI**: `--json` flag for machine-readable output on `status` and `traces`

## [0.3.1] — 2026-02-19

### Fixed
- SDK decorators (`@trace_agent`, `@trace_tool`, `@trace_llm`) now auto-create a trace when no active context exists — fixes the "empty dashboard" bug where traces were silently dropped
- Default `LIGHTHOUSE_BASE_URL` changed from `http://localhost:8000` to `https://agent-lighthouse.onrender.com` for zero-config production usage

### Added
- `on_chat_model_start` handler in LangChain adapter for modern chat models (ChatOllama, ChatOpenAI)
- Backend support for Supabase-generated API keys (`lh_` prefix) in the `api_keys` table
- `get_user_id_by_api_key` reverse lookup in API key service

## [0.3.0] — 2026-02-12

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
- UI iconography migrated from emoji to icon components
- Dockerfiles hardened to run as non-root users

### Fixed
- SDK tracer context consistency for decorator-based instrumentation
- SDK package metadata now points to the correct repository
