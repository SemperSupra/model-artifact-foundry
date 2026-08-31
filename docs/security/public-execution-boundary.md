# Public Execution Security Boundary

## Trust direction

Public workflows must not receive credentials that can read private Foundry/consumer repositories. Public execution emits public evidence and immutable artifact identities; any private evaluation may consume that public evidence separately.

## Pull-request context

Untrusted pull-request jobs must be read-only/minimally privileged and must not receive package-write authority. Do not use `pull_request_target` patterns that execute untrusted checkout content with elevated permissions.

## Trusted publication context

When publication workflows are introduced later, they must:

- execute only trusted repository code/state;
- use least-privilege `GITHUB_TOKEN` permissions;
- pin third-party Actions by full commit SHA;
- bind publication evidence to exact repository revision and exact artifact digest;
- keep candidate publication distinct from approved-catalog promotion;
- never print credentials or token material.

## Upstream content

Generic acquisition treats upstream artifacts as untrusted data.

- Do not execute arbitrary upstream scripts or `trust_remote_code`-style content.
- Artifact-family profiles must define allowed formats/file patterns.
- Ambiguous or executable serialization formats require explicit additional review/isolation before support.
- Missing/unknown/custom/gated/restricted license state fails closed for automatic mirroring.

## Claims boundary

Integrity, provenance, structural inspection, and bounded family smoke tests do not prove generic model safety, security, or quality. Evidence must name the exact claim established by each validator.

## Supply-chain evidence

Future candidate publication should record exact upstream revision, file inventory/hashes, license/provenance snapshot, validator/tool versions, OCI digest, and pull-back verification. Approved catalog entries must reference immutable candidate evidence.
