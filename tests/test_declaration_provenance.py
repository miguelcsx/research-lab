from pathlib import Path

import rlab


def test_imperative_declarations_keep_their_source_file(tmp_path: Path) -> None:
    project = rlab.Project("provenance-test", root=tmp_path)

    project.pipeline("project.clean")
    project.dataset("project.clean", pipeline="project.clean")

    records = {record["kind"]: record for record in project.records}
    expected = Path(__file__).resolve()

    assert Path(records["pipeline"]["source"]).resolve() == expected
    assert Path(records["dataset"]["source"]).resolve() == expected
