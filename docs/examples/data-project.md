# Data project

This project exposes one typed dataset recipe from `ingest/corpus.py`:

```python
from collections.abc import Iterable

import rlab


def clean(
    records: Iterable[dict[str, object]],
    ctx: rlab.DataContext,
) -> Iterable[dict[str, object]]:
    del ctx
    for record in records:
        text = str(record["text"]).strip()
        if text:
            yield {**record, "text": text}


def nonempty(rows: list[dict[str, object]], ctx: rlab.DataContext) -> rlab.CheckResult:
    del ctx
    return rlab.CheckResult(bool(rows))


@rlab.dataset("corpus.clean-v1", stages=(clean,), checks=(nonempty,))
def source(ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
    del ctx
    yield {"id": "1", "text": "  Hello world  ", "source": "web"}
    yield {"id": "2", "text": "Research lab", "source": "book"}
```

Load the module from `lab.toml`:

```toml
[modules]
load = ["ingest.corpus"]
```

Then build and inspect it:

```bash
rlab data build dataset:corpus.clean-v1
rlab data profile runs/<run-id>/artifacts/dataset/manifest.yaml
rlab data sample runs/<run-id>/artifacts/dataset/manifest.yaml --n 5
```
