# Refactor audit and migration policy

No historical artifact is deleted before the new workflow passes Tc regression
tests.

## Keep

- `src/comproscanner`: publisher/PDF processors, agents, tools, evaluation,
  cleaning, knowledge graph, and visualization capabilities.
- accepted Gold and final prediction JSON.
- Tc preset and validated scientific instructions.
- useful unit, integration, and regression tests.
- discovery and lawful open-access acquisition utilities.

## Migrate after equivalence validation

- root `pdfs/*.pdf` into `pdfs/manual` or an indexed normalized collection,
  without changing Paper 1-100 identities.
- API downloads into provider-specific `pdfs/downloaded/*` directories.
- curated artifacts into `outputs/gold`, `outputs/metrics`,
  `outputs/literature`, and `outputs/reports`.
- reproducible execution artifacts into `outputs/runs/<run_id>`.

## Delete only after replacement is verified

- batch-specific runners replaced by the CLI.
- one-off debug scripts, caches, traces, and duplicated reports.
- unrelated large upstream example corpora and example generated databases.
- regenerable `work` data that is not needed for a frozen benchmark.

## Completed in the current refactor

- Removed the large upstream piezoelectric/VLM benchmark corpora, generated
  model logs, and paper-figure assets under `examples/`; the reusable VLM,
  equation, RAG, evaluation, and visualization implementations remain in
  `src/comproscanner`.
- Added guarded `discover` and `acquire-oa` CLI commands backed by reusable
  modules under `src/comproscanner/literature`.
- Made package and CLI imports lazy so local commands do not initialize model
  providers or telemetry.
- Added a guarded `process-articles` command and source registry so local PDFs
  and all four publisher processors share one validated execution entry point.
- Fixed test isolation so selecting only lightweight CLI tests does not import
  optional database/embedding dependencies.

The existing user deletion under `output/pdf` is intentionally not modified or
staged by this refactor.
