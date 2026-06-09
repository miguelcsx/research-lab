from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest

from rlab.benchmarks.context import BenchmarkContext
from rlab.components.builders import build_component
from rlab.components.loader import load_component
from rlab.components.specs import BuildSpec, ComponentSpec
from rlab.config.defaults import DEFAULT_CONFIG
from rlab.context.project import find_project
from rlab.context.runtime import RuntimeContext
from rlab.errors import ConfigError
from rlab.external.command import ExternalCommand
from rlab.launchers import DockerLauncher, LocalLauncher, SubprocessLauncher
from rlab.references.parser import parse_reference
from rlab.testing import FakeTokenizer, count_tokens


@runtime_checkable
class Tokenizer(Protocol):
    """Project-defined component contract — rlab does not ship domain protocols."""

    def encode(self, text: str) -> list[int]: ...

    def decode(self, ids: list[int]) -> str: ...


def test_context_component_and_testing_helpers(project: Path, runtime: RuntimeContext) -> None:
    assert find_project(project / "components") == project
    with pytest.raises(ConfigError):
        find_project(project.parent)

    tokenizer = build_component(runtime.registry, "tokenizer:project.byte")
    assert isinstance(tokenizer, Tokenizer)
    assert tokenizer.decode(tokenizer.encode("x")) == "x"
    loaded = load_component(runtime.registry, "tokenizer:project.byte")
    assert isinstance(loaded, Tokenizer)
    assert loaded.encode("x")
    with pytest.raises(TypeError, match="must be FakeTokenizer"):
        build_component(
            runtime.registry,
            "tokenizer:project.byte",
            expected=FakeTokenizer,
        )
    assert BuildSpec(component=ComponentSpec(ref=parse_reference("tokenizer:project.byte"))).cache
    assert DEFAULT_CONFIG.tracking.backend == "local"

    fake = FakeTokenizer()
    assert fake.decode(fake.encode("ab")) == "xx"
    context = BenchmarkContext(runtime=runtime, benchmark="fake", target="tokenizer:fake")
    assert count_tokens(fake, context) == {"tokens": 4.0}
    with pytest.raises(RuntimeError):
        runtime.artifact_path("x")


def test_launchers(tmp_path: Path) -> None:
    command = ExternalCommand(args=("python", "-c", "print('ok')"), cwd=tmp_path)
    assert LocalLauncher(tmp_path).launch(command).stdout.strip() == "ok"
    assert SubprocessLauncher(tmp_path).launch(command).returncode == 0
    assert DockerLauncher(tmp_path).command("image", "echo", "ok").args[:3] == (
        "docker",
        "run",
        "--rm",
    )
