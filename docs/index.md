# ComProScanner

This project provides one evidence-first workflow for extracting traceable
material-property Facts from local PDFs and publisher content.

Start with the [architecture](architecture.md), then follow the
[quick start](getting-started/quick-start.md). Optional tools are described as
[extension points](extensions.md). The original ComProScanner interfaces and
documentation remain available under [legacy compatibility](legacy.md).

The production boundary is:

```text
Article -> Evidence -> Fact -> human review -> Gold / database export
```
