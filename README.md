# ComProScanner — evidence-first materials extraction

This fork keeps the reusable acquisition, parsing, RAG, equation, vision,
database, evaluation, and visualization capabilities of ComProScanner while
providing one traceable production workflow for material-property extraction.
The currently validated property is Curie temperature (Tc).

## Production workflow

```text
discovery / local PDFs / publisher XML
  -> canonical Article
  -> canonical TextChunks and non-text source units
  -> pluggable Evidence providers
  -> Qwen identifier
  -> DeepSeek property extraction
  -> normalized and conservatively merged Facts
  -> review workbook
  -> accepted Gold and strict evaluation
```

Every Fact links to original Evidence. Rules and PhysBERT are retrieval methods
over the same canonical chunks, not separate pipelines. Tables, figures, and
equations use the same Evidence contract. The historical ComProScanner workflow
remains available as a compatibility layer, not the production orchestrator.

## Data layout

```text
pdfs/
├─ manual/       # user-supplied PDFs
├─ downloaded/   # API-acquired PDFs separated by source
├─ normalized/   # corpus manifests; no duplicate PDF copies
└─ quarantine/   # invalid or unresolved files

work/            # disposable intermediate data
outputs/
├─ gold/         # human-reviewed facts
├─ runs/         # durable prediction runs
├─ metrics/      # evaluation results
├─ literature/   # discovery and download manifests
└─ reports/      # reports and presentations
```

## Installation

Python 3.12 or 3.13 is required. Install only needed capabilities:

```bash
pip install -e .
pip install -e .[pdf]
pip install -e .[rag]
pip install -e .[database,visualization]
pip install -e .[legacy]
```

`pip install -e .[all]` installs every optional capability.

## Run without batch scripts

Commands are guarded. Planning does not parse PDFs, access networks, or call
models.

```bash
comproscanner init-corpus --root pdfs
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo --through prepare --execute-pipeline
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo --execute-pipeline --execute-models
comproscanner run --source manual_pdf --folder pdfs/manual/original_001_100 --run-id tc_demo --execute-pipeline --execute-models --resume
```

Use `comproscanner --help` for discovery, acquisition, normalization,
processing, Evidence, extraction, review, and evaluation commands.

## Extension points

- New property: register a `PropertyExtractionPreset`.
- New article source: produce the canonical Article contract.
- New retrieval or modality: register an Evidence provider.
- New material parser: implement a Fact processor.
- New database or visualization: consume reviewed Facts.

See [architecture](docs/architecture.md), [Evidence](docs/evidence.md),
[extensions](docs/extensions.md), and [legacy compatibility](docs/legacy.md).

## Provenance

This project is based on the original
[ComProScanner](https://github.com/slimeslab/ComProScanner), described in
Digital Discovery, DOI
[10.1039/D5DD00521C](https://doi.org/10.1039/D5DD00521C). The upstream license,
citation file, and reusable tools are retained.
