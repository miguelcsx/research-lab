from pathlib import Path

from rlab._loader import load_modules


def test_load_modules_walks_namespace_packages(tmp_path: Path) -> None:
    package = tmp_path / "experiments"
    package.mkdir()
    (package / "sweep.py").write_text(
        "import rlab\n"
        "lab = rlab.Project()\n"
        "@lab.experiment('sweep')\n"
        "def sweep(ctx):\n"
        "    return {'ok': True}\n"
    )

    project = load_modules(tmp_path, ["experiments"], strict=True)

    assert project.record("experiment", "sweep")["name"] == "sweep"
