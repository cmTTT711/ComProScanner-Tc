# ComProScanner project architecture

This repository keeps the public ComProScanner processors and tools, and adds a
traceable evidence-first workflow for material-property extraction.

## Corpus boundary

`pdfs/manual/` is reserved for user-supplied PDFs. API downloads go to a
source-specific directory under `pdfs/downloaded/`. Files accepted by the
normalizer are represented in `pdfs/normalized/`; invalid inputs go to
`pdfs/quarantine/`. Discovery metadata and manifests belong under
`outputs/literature/`, never beside the PDFs.

`comproscanner init-corpus --root pdfs` creates this layout locally and makes
no network or model calls.

## Side-effect boundaries

- `presets`, `init-corpus`, `prepare-evidence`, `review`, and `evaluate` are
  local commands.
- `process-articles` is plan-only by default. Actual parsing requires
  `--execute-processing`; a network-backed source additionally requires
  `--execute-network`.
- `discover` and `acquire-oa` require `--execute-network`.
- `extract` requires `--execute`.
- Importing `comproscanner` or showing CLI help does not load CrewAI, LiteLLM,
  embedding models, or telemetry.

## Canonical normalization

Publisher and PDF processors may retain their format-specific parsing logic,
but their CSV outputs converge through one command:

```bash
comproscanner normalize --csv first.csv --csv second.csv --output article.csv
```

The command sanitizes NUL bytes, upgrades legacy columns, validates the schema,
and de-duplicates by `document_id`. `comproscanner sources` lists the registered
raw inputs and their credential/network requirements.

The processor entry point is likewise shared:

```bash
comproscanner process-articles --source manual_pdf --folder pdfs/manual
comproscanner process-articles --source downloaded_pdf --folder pdfs/downloaded/elsevier
comproscanner process-articles --source springer --doi-file dois.txt
```

These examples only print validated plans. The first two map to the existing
`PDFsProcessor`; publisher names map to their existing processors. Local plans
disable DOI/metadata lookups unless network execution is explicitly enabled.
This preserves parsing behavior while removing the need for a new Python runner
for each batch.

## Stable pipeline

```text
paper discovery
  -> lawful full-text acquisition
  -> PDF or publisher-XML processor
  -> canonical article CSV
  -> canonical TextChunks and non-text source units
  -> Evidence
  -> per-Evidence identifier
  -> per-Evidence extractor
  -> Fact processors and conservative merge
  -> prediction JSON and review workbook
  -> accepted Gold and strict evaluation
```

The current validated domain is Curie temperature. Scientific inclusion policy
remains in `presets/curie_temperature.py`; processing, paths, models, and batch
selection do not belong in that preset.

## Data contracts

`schemas/article_csv.py` defines the CSV columns shared by local PDFs and every
publisher processor. Historical processor frames pass through a non-lossy
adapter while processors are migrated. Missing sections are allowed; missing
columns or document identifiers are not.

`chunking/text_chunker.py` produces the only normal-text segmentation. Chunks
never cross section boundaries, prefer natural paragraphs, and split oversized
paragraphs with overlap. Fixed three-sentence context is not used.

## Evidence

Evidence preserves original article content. It does not classify statements as
background, cited work, or current work.

- `TextEvidence`: one canonical TextChunk selected by rules, PhysBERT, or both.
- `TableEvidence`: caption, headers, selected rows, units, and footnotes.
- `FigureEvidence`: original image reference, caption, nearby original text, and
  later vision output.
- `EquationEvidence`: equation and its nearby original explanatory text.

Rules and RAG are retrieval methods, not different evidence types. Both operate
on the same TextChunk collection and return `chunk_id`. If both select one chunk,
the model sees it once and the evidence records both methods.

## Agent boundary

Each Evidence is handled independently. Qwen performs the identifier decision;
accepted text/table/equation Evidence is extracted by DeepSeek. Figure pixels
require a configured vision model before their result is formatted. One
Evidence failure does not stop later Evidence or papers.

External calls require an explicit CLI execution flag. Preparing CSV, chunks,
Evidence, manifests, and review structures is local-only.

## Configurable execution

The property preset declares the default Evidence providers. A run may override
them without editing the pipeline by repeating `--provider`. Provider factories
are resolved through `EvidenceProviderRegistry`; `physbert` uses the same
canonical chunks as rule retrieval and remains opt-in because it loads a local
embedding model.

`comproscanner run` accepts an Article CSV, processor CSVs, or registered raw
PDF/publisher sources. Raw processors execute in the run's own
`processor_workspace`, then normalize into that run's canonical `article.csv`
before Evidence preparation, extraction, review, and evaluation. It prints a
plan by default. `--execute-pipeline` permits processing and local stages,
`--execute-models` permits Qwen/DeepSeek/VLM stages, and `--execute-network`
separately permits publisher and optional network tools such as Material
Parsers.

Each stage is recorded in `stage_status.json`; Evidence preparation checkpoints
each document and extraction checkpoints each Evidence. `--resume` skips those
completed records, including recorded failures, so an interruption or one bad
paper does not repeat completed work. Replacement is explicit through
`--force`, which is mutually exclusive with `--resume`.

Fact normalization is also pluggable. The safe default preserves the exact
reported material. `material-parser-api` adapts the historical formula parser
without importing CrewAI, caches repeated formulas, and falls back to the
reported material if the service cannot resolve a value.

## Facts and review

Facts retain reported and normalized material names, value, qualifier, unit,
conditions, and every supporting `evidence_id`. Initial merging is deliberately
strict: no implicit K/°C conversion, tolerance merge, or approximate-value
collapse.

The review workbook uses one Fact per row and combines all supporting original
Evidence into one visible cell. Human `ACCEPT`, `REJECT`, or `MODIFY` decisions
produce Gold; prediction runs never overwrite Gold.

## Extension boundary

New properties define a preset: scientific scope, signals, units, vector
queries, and model instructions. New source-finding tools implement an Evidence
provider. New normalization tools implement a Fact processor. New exports,
metrics, graphs, or visualizations implement a result processor. None requires
copying the PDF processors or the main workflow.
