# Data project

This project exposes a reusable, audited dataset from `ingest/corpus.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass

import rlab


@rlab.source("corpus.raw")
@dataclass(frozen=True, slots=True)
class CorpusSource:
    def read(self, ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
        del ctx
        yield {"id": "1", "text": "  Hello world  ", "source": "web"}
        yield {"id": "2", "text": "", "source": "book"}


@rlab.transform("corpus.clean")
@dataclass(frozen=True, slots=True)
class Clean:
    def apply(self, record, ctx):
        del ctx
        text = str(record["text"]).strip()
        if not text:
            return rlab.data_drop("empty")
        return rlab.data_update({**record, "text": text}, reason="trimmed")


@rlab.pipeline(
    "corpus.clean",
    stages=(rlab.use("transform:corpus.clean"),),
)
class CleanPipeline:
    pass


@rlab.dataset(
    "corpus.clean",
    source=rlab.use("source:corpus.raw"),
    pipeline="pipeline:corpus.clean",
    sinks=(rlab.use("sink:rlab.jsonl"),),
    audit=rlab.AuditPolicy(sample_reasons={"empty": 5}),
)
class CleanCorpus:
    pass
```

```bash
rlab data build dataset:corpus.clean
rlab data profile runs/<run-id>/artifacts/dataset/manifest.yaml
rlab data audit runs/<run-id>
```
