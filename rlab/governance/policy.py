import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class LabPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    require_hypothesis: bool = False
    require_data_manifest: bool = False
    require_clean_git_for_promotion: bool = False
    require_review_for_paper: bool = False
    forbidden_env_patterns: tuple[str, ...] = ("*_TOKEN", "*SECRET*", "*KEY*", "*PASSWORD*")
    allowed_artifact_visibilities: tuple[str, ...] = ("private", "team", "public", "paper")

    @classmethod
    def load(cls, root: Path) -> "LabPolicy":
        path = root / "lab.policy.toml"
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            raw = tomllib.load(f)
        # Flatten nested sections ([required], [forbidden]) into flat dict
        data: dict[str, object] = {}
        for section, value in raw.items():
            if isinstance(value, dict):
                data.update(value)
            else:
                data[section] = value
        return cls.model_validate(data)

    def check_env(self, env: dict[str, str]) -> list[str]:
        import fnmatch
        violations: list[str] = []
        for key in env:
            for pattern in self.forbidden_env_patterns:
                if fnmatch.fnmatch(key.upper(), pattern.upper()):
                    violations.append(f"Env var {key!r} matches forbidden pattern {pattern!r}")
                    break
        return violations
