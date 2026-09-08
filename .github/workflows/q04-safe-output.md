---
on:
  workflow_dispatch:
permissions: read-all
engine: copilot
safe-outputs:
  create-issue:
    title-prefix: "[Q04 SAFE OUTPUT] "
    max: 1
---

# Q0.4 Safe-output composition fixture

This workflow is a compiler-only qualification fixture. If it were ever executed with an engine, the agent would be asked to propose at most one harmless issue containing the text `Q04_SAFE_OUTPUT_FIXTURE`. Do not execute the compiled agentic workflow as part of Q0.4; this source exists only to inspect how `gh-aw` compiles intent, agent permissions, and separately scoped safe-output actuation.
