# RAG configuration

PhysBERT retrieval is an optional Evidence provider. It searches the same
canonical TextChunks used by rule retrieval and returns chunk IDs; it does not
create a parallel article representation or directly write Facts.

Install the optional dependencies with `pip install -e .[rag]`, then select
`physbert` with the CLI `--provider` option. When rules and PhysBERT select the
same chunk, the Evidence is sent once and records both retrieval methods.
