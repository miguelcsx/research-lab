from pathlib import Path

import rlab


def test_runtime_workflow_specs_keep_their_source_file(tmp_path: Path) -> None:
    project = rlab.Project("provenance-test", root=tmp_path)

    @project.workflow("prepare")
    def prepare(ctx: rlab.RuntimeContext) -> None:
        del ctx

    records = {(record["kind"], record["name"]): record for record in project.records}
    expected = Path(__file__).resolve()
    workflow_source = records[("workflow", "prepare")]["source"]
    assert isinstance(workflow_source, str)

    assert Path(workflow_source).resolve() == expected


def test_decorators_are_project_bound() -> None:
    for name in (
        "experiment",
        "workflow",
        "study",
        "benchmark",
        "evaluation",
        "adapter",
        "loader",
        "executor",
        "resolver",
        "exporter",
        "reporter",
        "notifier",
    ):
        assert not hasattr(rlab, name)
        assert hasattr(rlab.Project(), name)


def test_generic_declaration_apis_are_not_public(tmp_path: Path) -> None:
    project = rlab.Project("no-generic-declarations-test", root=tmp_path)

    assert not hasattr(project, "declare")
    assert not hasattr(project, "declaration")
