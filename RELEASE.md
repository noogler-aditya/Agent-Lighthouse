# Release Process

## Versioning Policy

This project follows Semantic Versioning:

- `MAJOR`: breaking API or behavior changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible fixes

## Release Prerequisites

Before cutting a release:

1. CI must pass on `main`.
2. Changelog must be updated under [CHANGELOG.md](CHANGELOG.md).
3. Security-impacting changes must be documented.
4. Migration notes must exist for breaking changes.

## Release Steps

1. Update version in `sdk/pyproject.toml` and `sdk/agent_lighthouse/__init__.py`.
2. Update `CHANGELOG.md` with the new version's entries.
3. Merge into `main` after all required checks pass.
4. Tag release (`vX.Y.Z`) — this triggers:
   - PyPI publish via `.github/workflows/publish-sdk.yml`
   - GitHub Release via `.github/workflows/release.yml`
   - Docker images via `.github/workflows/cd.yml`
5. Verify on [PyPI](https://pypi.org/project/agent-lighthouse/) that the new version is live.
6. Validate with: `pip install --upgrade agent-lighthouse && agent-lighthouse status`

## Post-Release Validation

After release/tag:

- Pull and run latest backend/frontend images from GHCR.
- Verify `/health` and `/api/traces` with API key auth.
- Run SDK smoke script against release environment.

## Rollback Guidance

- If release is unhealthy, revert the merge commit or hotfix on top of `main`.
- Publish a patched version with clear incident notes in the changelog.
