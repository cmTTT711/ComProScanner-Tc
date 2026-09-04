# Legacy compatibility

The original ComProScanner public API, CrewAI extraction flow, data cleaning,
semantic evaluation, database, RAG, equation, graph, and visualization tools
remain available for compatibility and future adapters.

They are not the production orchestration path for the evidence-first workflow.
New runs should use `comproscanner run` or its individual stage commands. New
features should produce Article, Evidence, Fact, or reviewed-result contracts
instead of adding another end-to-end runner.

Historical upstream guides and news are retained under
`docs/legacy/upstream-user-guide/` and `docs/legacy/upstream-news/`. Their paths,
defaults, and output formats describe the upstream workflow and must not be
treated as current run instructions.
