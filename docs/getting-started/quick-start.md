# Quick start

```bash
comproscanner init-corpus --root pdfs
comproscanner presets
comproscanner sources
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo
```

The last command prints a plan. Add `--execute-pipeline` for local stages and
`--execute-models` only when external model calls are intended. Use `--resume`
to continue a checkpointed run.
