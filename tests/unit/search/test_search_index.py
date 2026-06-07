from __future__ import annotations

from pathlib import Path

from rlab.search.index import SearchIndex


def test_search_index_basic_filter_delete_and_upsert(tmp_path: Path) -> None:
    index = SearchIndex(tmp_path / "search.db")
    index.index("run:001", "run", "vocab_size experiment", "question: how does vocab size affect loss?")
    index.index("art:001", "artifact", "vocab artifact", "artifact body text")

    assert any(result["id"] == "run:001" for result in index.search("vocab"))
    assert all(result["kind"] == "run" for result in index.search("vocab", kinds=("run",)))

    index.index("run:001", "run", "updated title", "updated body with new_term_abc")
    assert any(result["id"] == "run:001" for result in index.search("new_term_abc"))

    index.delete("run:001")
    assert not index.search("new_term_abc")
    assert not index.search("xyznomatch_unique_999")
