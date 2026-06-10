# References

References are strings that identify things inside or outside an `rlab` project.

## General syntax

```text
<scheme>:<value>
<scheme>:<value>@<alias-or-version>
```

Examples:

```text
tokenizer:project.byte
model:project.constant
benchmark:project.tokenizer.length
suite:project.quick
dataset:project.tiny
manifest:babylm_clean
run:experiment_abc
artifact:dataset/project.tiny@candidate
hf:gpt2
local:models/checkpoint.pt
```

Data declarations use concise semantic schemes:

```text
source:project.raw
transform:text.clean
filter:quality.symbols
group:text.documents
dedup:text.simhash
sink:project.corpus
check:dataset.nonempty
metric:dataset.records
pipeline:project.clean
dataset:project.clean
patterns:project.text
```

## Component references

A component reference uses the component kind as the scheme:

```text
tokenizer:project.byte
model:project.constant
solver:project.basic
compiler:clang_17
```

The decorator that creates those references is:

```python
@rlab.component("tokenizer", "project.byte")
class ByteTokenizer:
    ...
```

Internally this is stored as an `EntryKind.COMPONENT` record with the registry name:

```text
tokenizer:project.byte
```

## Artifact references

Artifacts have an extra sub-kind:

```text
artifact:<artifact-kind>/<name>@<version-or-alias>
```

Examples:

```text
artifact:dataset/project.tiny@candidate
artifact:model/small-transformer@approved
artifact:evaluation/project.quick@latest
```

Artifact aliases are human labels such as `candidate`, `approved`, `latest`, or `paper`.

## Dataset manifest references

Manifest references point to files under configured manifest directories:

```text
manifest:clean_corpus_v1
```

`rlab` searches for:

```text
manifests/clean_corpus_v1.yaml
manifests/clean_corpus_v1.yml
```

Then it validates checksums before using the manifest.

## External references

`rlab` supports reference kinds for external ecosystems:

```text
hf:gpt2
hf_dataset:wikitext
torch:resnet50
mlflow:run-id
s3:bucket/key
gcs:bucket/key
```

Core `rlab` parses these references, but actual integration behavior depends on the project code or optional adapters.

## Good naming conventions

Use stable, searchable names:

```text
project.byte
babylm.clean_v1
compiler.llvm_o3
solver.fdtd_yee
eval.math_v1
```

Avoid names like:

```text
test
new
final
best
tmp
```

Use aliases for lifecycle labels and versions for immutable identity.
