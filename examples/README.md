# Examples

The CLI is the supported execution entry point. A new batch does not require a
new Python runner.

```bash
# Inspect the plan only
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo

# Parse PDFs and prepare Evidence locally
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo --through prepare --execute-pipeline

# Explicitly permit configured model calls
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo --execute-pipeline --execute-models
```

Use `comproscanner --help` and `comproscanner <command> --help` for stage-level
commands. Property extensions belong in `src/comproscanner/presets/`; Evidence
extensions belong in `src/comproscanner/evidence/providers/`.
