# Data project

This project exposes one typed dataset recipe from `ingest/corpus.py`:

```python
from collections.abc import Iterable

import rlab


def raw(ctx: rlab.DataContext) -> Iterable[dict[str, object]]:
    del ctx
    yield {"id": "1", "text": "  Hello world  ", "source": "web"}
    yield {"id": "2", "text": "Research lab", "source": "book"}


def clean(
    records: Iterable[dict[str, object]],
    ctx: rlab.DataContext,
) -> Iterable[dict[str, object]]:
    del ctx
    for record in records:
        text = str(record["text"]).strip()
        if text:
            yield {**record, "text": text}


flow = rlab.DataFlow.from_source(
    rlab.FunctionSource(rlab.SourceId("corpus.raw"), raw)
).then(rlab.FunctionStage(rlab.StageId("corpus.clean"), clean))

CLEAN = rlab.DatasetRecipe(
    id=rlab.DatasetId("corpus.clean-v1"),
    flow=flow,
    sinks=(rlab.JsonlSink(),),
    checks=(
        rlab.FunctionCheck(
            rlab.CheckId("corpus.nonempty"),
            lambda rows, _ctx: rlab.CheckResult(bool(rows)),
        ),
    ),
)

rlab.register_datasets(rlab.DatasetCatalog(CLEAN))
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
