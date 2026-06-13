from pathlib import Path

import rlab


def test_imperative_declarations_keep_their_source_file(tmp_path: Path) -> None:
    project = rlab.Project("provenance-test", root=tmp_path)

    project.pipeline("project.clean")
    project.dataset("project.clean", pipeline="project.clean")

    records = {record["kind"]: record for record in project.records}
    expected = Path(__file__).resolve()
    pipeline_source = records["pipeline"]["source"]
    dataset_source = records["dataset"]["source"]
    assert isinstance(pipeline_source, str)
    assert isinstance(dataset_source, str)

    assert Path(pipeline_source).resolve() == expected
    assert Path(dataset_source).resolve() == expected


def test_decorators_are_project_bound() -> None:
    for name in (
        "experiment",
        "workflow",
        "component",
        "dataset",
        "evaluation",
        "adapter",
    ):
        assert not hasattr(rlab, name)
        assert hasattr(rlab.Project(), name)
