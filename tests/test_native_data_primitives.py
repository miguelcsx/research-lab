from __future__ import annotations

import rlab
from rlab.data import DocumentAssembler, FilterRule, SimhashDedup, TextFilter


def test_native_text_filter_rules_and_boundaries() -> None:
    boundary = rlab.DataBoundary({"source": "unit", "origin": "base"}, "source")
    stage = TextFilter(
        [
            FilterRule.url(),
            FilterRule.word_count(minimum=1, maximum=4),
            FilterRule.symbol_ratio(maximum=0.5),
        ]
    )

    assert stage.apply(boundary).record is boundary
    assert stage.apply({"text": "hello"}).action == "keep"
    assert stage.apply({"text": "https://example.com"}).reason == "contains_url"
    assert stage.apply({"text": "one two three four five"}).reason == "too_many_words"


def test_native_simhash_dedup_preserves_first_record() -> None:
    records = [
        {"source": "unit", "text": "hello world hello world hello world"},
        {"source": "unit", "text": "hello world hello world hello world"},
    ]

    assert SimhashDedup(near_min_words=3).apply(records) == [records[0]]


def test_native_document_assembler_flushes_on_boundary() -> None:
    records = [
        {"source": "a", "origin": "base", "text": "one two"},
        rlab.DataBoundary({"source": "a", "origin": "base"}, "source"),
        {"source": "b", "origin": "base", "text": "three four"},
    ]

    docs = DocumentAssembler(min_document_words=1).apply(records)

    assert [doc["source"] for doc in docs] == ["a", "b"]
    assert [doc["word_count"] for doc in docs] == [2, 2]
