# Public Bodu PST corpus — immutable reference-only Foundry candidate

## Purpose and scope

This is an experimental `dataset` family member under the draft benchmark
declaration contract, not a newly created model or an approved distribution.
Use one logical identity `dataset/pst/bodu-pstsdk-v14-v23-four` and four
distinct immutable source file digests to join observations made by independent
PST readers or fixture-producing applications. Consumer CI may validate *this
text manifest*, not automatically fetch the PST files.

The four 271,360-byte source candidates originate from the public Bodu/pstsdk
test inventory. The SHA-256 pins are **published source-inventory observations**
and have not been independently rehashed from bytes by this PR. The source
file listing reported by `lspst` is not an independent truth of native
MAPI properties, attachments, or completeness.

| Component | MS-PST version | Upstream-listed folders | Upstream-listed messages |
| --- | ---: | ---: | ---: |
| unicode-v23-one-message | 23 | 1 | 1 |
| unicode-v23-zero-message | 23 | 1 | 0 |
| ansi-v14-one-message | 14 | 1 | 1 |
| ansi-v14-zero-message | 14 | 1 | 0 |

Exact SHA-256 values, upstream repository revision, source path locators,
rights evidence, and independent promotion gating are in
`examples/benchmarks/pst-bodu-pstsdk-four.json`. The 40-character exact
source commit is not a mutable tag. Source path aliases are allowed **only
after their byte digest is independently verified**; file basenames and
upstream labels alone never prove identity.

## Foundry lifecycle and owner gates

- **DECLARED / candidate:** this manifest is all that has been created here.
  The fixture bytes have **not** been downloaded, mirrored, published to OCI,
  catalog-approved, or hydrated by this change.
- **RESOLVED / source observation:** an authorized source-local acquisition
  may pin exact source bytes by sha256 and length, record acquisition UTC,
  upstream revision, and any mismatched/truncated/replaced payload.
- **RIGHTS REVIEW:** upstream NOTICE suggests an Apache-2.0 provenance
  context, but per-binary redistribution and data classification have not
  been independently resolved. Until then **no public mirror, GHCR package,
  cloud upload, or promotion**; manifest-only is intentional.
- **CONSUMER SELECTED / qualified:** downstream readers use the identical
  digest but retain independent support claims and oracle findings for each
  format and item class. Structural parsing of v23 does **not** imply v14
  support, native attachment recovery, or native class completeness.
- **MATERIALIZED / VERIFIED:** a later approved bounded local cache may
  hydrate from exact pinned source, reject digest/size mismatches, keep
  immutable originals, and create mutated copies as separate derived
  artifacts with parent digest + mutation recipe + resultant digest.
- **PUBLIC VS RESTRICTED:** publicly encountered mail-bearing samples,
  private archives, OST caches, personal/work exports, and any resulting
  extracted content are outside this public declaration. They require
  independently classified *private* references and authorized storage;
  source byte hashes of sensitive private material must not be projected
  publicly.

## Parallel-consumer comparison

Independent consumers can already work in parallel against the same declared
source identity:

1. **Restricted reader** can validate header version, root/BREF, bounded
   Unicode BTPAGE/BBTENTRY/NBTENTRY and fail-closed mutation behavior
   without adding a native/runtime dependency.
2. **General ingestion reader** can separately qualify candidate parsers,
   native classes, raw properties, relationships, and recoverable attachments.
3. **Producer/oracle** captures original source-authored class/attachment
   intentions, independent native reader observations, byte hash checks,
   and discrepancy receipts. Upstream `lspst` item counts are only a small
   preliminary expectation, not a universal gold oracle.

Cross-project comparison accepts observations only with the same immutable
fixture digest, exact reader version, scope, independence status, and
`PASS / PARTIAL / UNSUPPORTED / FAILED / UNKNOWN` semantics.
Do not make consumer release versions or implementation schedules lock step.
Do not put run timestamps into stable artifact identity.

## Bounded acceptance of this PR

It must pass the existing experimental Foundry benchmark validator and the
new four-case source-identity/rights regression test on clean public CI.
That establishes only metadata integrity and deliberate non-redistribution.
A real archive/hydration/reader result requires separate admitted execution
and explicit Foundry promotion authority.
