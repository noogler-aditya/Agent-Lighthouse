# Governance

## Project Model

Agent Lighthouse follows a maintainer-led governance model.

- Maintainers are responsible for roadmap decisions, reviews, security handling, and release approvals.
- Contributors can propose changes through issues and pull requests.
- Significant changes should be discussed in an issue before implementation.

## Decision Making

- Routine changes: approved by one maintainer review.
- High-impact changes (architecture, security model, CI/CD release behavior): require consensus from maintainers.
- In case of disagreement, maintainers prioritize security, backward compatibility, and operational reliability.

## Proposal Process

Use this flow for large or risky changes:

1. Open an issue describing problem, scope, and alternatives.
2. Capture proposed design and migration impact.
3. Wait for maintainer approval before implementation.
4. Submit PR with tests, docs, and rollout notes.

## Maintainer Responsibilities

- Keep CI/CD and branch protection healthy.
- Review community contributions in a timely manner.
- Keep documentation and changelog accurate.
- Coordinate security disclosures and patched releases.

## Enforcement References

- Community behavior: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Vulnerability handling: [SECURITY.md](SECURITY.md)
- Support handling: [SUPPORT.md](SUPPORT.md)
