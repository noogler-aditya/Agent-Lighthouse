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

1. Create release PR that updates version references and changelog.
2. Merge into `main` after all required checks pass.
3. Tag release (`vX.Y.Z`) in GitHub.
4. Publish GitHub release notes from changelog entries.
5. Validate container images pushed by CD to GHCR.

## Post-Release Validation

After release/tag:

- Pull and run latest backend/frontend images from GHCR.
- Verify `/health` and `/api/traces` with API key auth.
- Run SDK smoke script against release environment.

## Rollback Guidance

- If release is unhealthy, revert the merge commit or hotfix on top of `main`.
- Publish a patched version with clear incident notes in the changelog.
