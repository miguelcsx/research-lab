from __future__ import annotations

from dataclasses import dataclass

import pytest

import rlab
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.data.components import instantiate_component
from rlab.data.context import DataContext
from rlab.registry.context import using_registry


def has_url(record: dict[str, object]) -> bool:
    return "http" in str(record["text"])


def text_length(record: dict[str, object]) -> float:
    return float(len(str(record["text"])))


def test_declarative_regex_and_filter_utilities(
    runtime: RuntimeContext,
    tmp_path: object,
) -> None:
    with using_registry(runtime.registry):

        @rlab.patterns("test.patterns")
        @dataclass(frozen=True, slots=True)
        class Patterns:
            whitespace: str = r"\s+"
            heading: str = r"^#"

        @rlab.substitute(
            "test.normalize",
            field="text",
            patterns="patterns:test.patterns",
            substitutions=(rlab.RegexSubstitution("whitespace", " "),),
        )
        class Normalize:
            pass

        @rlab.classify(
            "test.classify",
            field="text",
            output_field="kind",
            patterns="patterns:test.patterns",
            rules=(rlab.ClassificationRule("heading", "heading", rlab.RegexMode.MATCH),),
            fallback="plain",
        )
        class Classify:
            pass

        @rlab.predicate("test.urls", predicate=has_url, reason="contains_url")
        class Urls:
            pass

        @rlab.threshold(
            "test.length",
            metric=text_length,
            metric_name="length",
            operator=rlab.ComparisonOperator.GREATER_THAN,
            threshold=5.0,
            reason="too_long",
        )
        class Length:
            pass

    ctx = DataContext(runtime=runtime, work_dir=runtime.paths.root)
    _, normalize = instantiate_component(
        runtime.registry,
        rlab.use("transform:test.normalize"),
        expected=(EntryKind.TRANSFORM,),
    )
    _, classify = instantiate_component(
        runtime.registry,
        rlab.use("transform:test.classify"),
        expected=(EntryKind.TRANSFORM,),
    )
    _, urls = instantiate_component(
        runtime.registry,
        rlab.use("filter:test.urls"),
        expected=(EntryKind.FILTER,),
    )
    _, length = instantiate_component(
        runtime.registry,
        rlab.use("filter:test.length"),
        expected=(EntryKind.FILTER,),
    )

    assert normalize.apply({"text": "a   b"}, ctx).record == {"text": "a b"}
    assert classify.apply({"text": "# title"}, ctx).record == {
        "text": "# title",
        "kind": "heading",
    }
    assert urls.apply({"text": "http://example.com"}, ctx).action is rlab.DataAction.DROP
    assert length.apply({"text": "lengthy"}, ctx).metrics == {"length": 7.0}


def test_declarative_utilities_reject_lambdas() -> None:
    with pytest.raises(ValueError, match="named function"):
        rlab.predicate("test.invalid", predicate=lambda _: True, reason="invalid")
