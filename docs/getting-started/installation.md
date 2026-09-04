# Installation

Use Python 3.12 or 3.13 in a dedicated environment.

```bash
pip install -e .[pdf]
```

Add only capabilities needed by the run: `rag`, `database`, `materials`,
`visualization`, or `legacy`. Use `.[all]` for the complete upstream toolset.
Credentials belong in `.env`; never commit that file.
