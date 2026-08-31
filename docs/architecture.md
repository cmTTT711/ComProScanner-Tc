# ComProScanner architecture

## Layer boundaries

ComProScanner is organized into four layers. Keeping these boundaries explicit
makes a new property adaptation independent from PDF ingestion and evaluation.

1. **Core library (`src/comproscanner`)** - publisher/PDF ingestion, candidate
   preparation, vector storage, extraction flows, cleaning, and evaluation.
2. **Property presets (`src/comproscanner/presets`)** - scientific scope,
   deterministic candidate signals, identifier policy, extraction notes, and
   output examples for one property. Presets must not contain API keys, paper
   selections, output paths, retry rules, or benchmark-specific state.
3. **Runners (`scripts`, `examples`)** - input selection, provider/model,
   timeout, isolation, checkpointing, and output locations.
4. **Artifacts (`outputs`)** - immutable predictions, accepted Gold, metrics,
   and user-facing reports. Regenerable runtime data belongs in ignored
   directories such as `work`, `db`, `logs`, `results`, and `tmp`.

## Generic extraction flow

```text
metadata or local PDF
  -> source-specific article processor
  -> normalized section CSV + optional figures
  -> deterministic property gate
  -> optional PhysBERT/Chroma index
  -> MatPropDataPreparator candidate text
  -> MaterialsDataIdentifierCrew
  -> CompositionExtractionCrew
  -> CompositionFormatCrew
  -> JSON result
  -> optional cleaner/evaluator/knowledge graph
```

The source dispatcher and public API are in `comproscanner.py`. Local PDF
conversion is in `article_processors/pdfs_processor.py` and
`utils/pdf_to_markdown_text.py`. Candidate construction is in
`utils/data_preparator.py`. The CrewAI orchestration is in
`extract_flow/main_extraction_flow.py`.

## Current Tc flow

The Tc domain policy is defined only in
`presets/curie_temperature.py`. It now uses `identifier_context_mode=hybrid`.
The complete deterministic candidate remains authoritative; PhysBERT/Chroma
retrieval can only append unique chunks and can never remove rule-derived text.
Missing or failed vector retrieval falls back to the complete rule candidate.
Qwen Flash performs the inexpensive yes/no identifier step, while DeepSeek
continues to perform composition--Tc extraction and formatting. A technical
Qwen failure retries the identifier once with the DeepSeek extraction model.

```text
local PDF
  -> Docling text/table extraction
  -> Tc candidate-pattern paper gate
  -> sentences containing digits or consecutive capitals, plus +/-1 sentence
  -> complete tables from results/discussion
  -> PhysBERT semantic retrieval (additive, fail-open)
  -> rule + retrieval merge and normalized deduplication
  -> Qwen Flash identifier (yes/no; DeepSeek technical fallback)
  -> DeepSeek composition/Tc extractor
  -> formatter
  -> prediction JSON
  -> independently accepted Gold evaluation
```

## Adding a property

Create one module under `presets`, return a `PropertyExtractionPreset`, and
register it in `presets/__init__.py`. Define:

- stable preset name;
- storage keyword and scientific extraction keyword;
- high-recall deterministic candidate patterns;
- identifier inclusion/exclusion policy;
- extraction and formatting notes;
- representative fixed/variable-composition examples.

Do not copy the PDF processors or extraction crews. Add property-specific schema
fields only when the generic fact model cannot preserve the science (for example
measurement conditions, uncertainty, inequality operators, or value ranges).

## Artifact policy

Only reproducible final deliverables belong in `outputs`. Runtime copies of PDFs,
Chroma indexes, raw logs, CrewAI storage, rendered review pages, pytest scratch
directories, and recovery attempts are disposable. API keys remain in `.env` and
must never be copied into artifacts.
