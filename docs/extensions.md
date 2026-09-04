# Extension points

The production workflow is extended through explicit contracts rather than a
second extraction pipeline.

## Add a property

Create and register a `PropertyExtractionPreset`. A preset owns scientific
scope, candidate signals, units, retrieval queries, and model instructions. It
does not own corpus paths, credentials, or output directories.

## Add an evidence source

Implement an Evidence provider and register it with
`EvidenceProviderRegistry`. Text rules and PhysBERT return the same canonical
TextChunk IDs. Table, figure, and equation providers return their corresponding
Evidence type. Providers never write final database rows.

## Add an article source

Register a processor with `ArticleSourceRegistry`. Its only production
responsibility is to produce the canonical Article schema. All later stages are
shared by PDFs and publisher XML.

## Add normalization or export

Material normalization implements the Fact processor contract. Database,
graph, and visualization integrations consume reviewed Facts; they do not
perform a parallel extraction.

Optional installation groups keep these capabilities removable:

```bash
pip install -e .[pdf]
pip install -e .[rag]
pip install -e .[database,visualization]
pip install -e .[legacy]
```
