import math

from pydantic import BaseModel, ConfigDict, Field


class DataMixReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sources: tuple[str, ...]
    proportions: dict[str, float]
    quality_scores: dict[str, float] = Field(default_factory=dict)
    domain_coverage: dict[str, float] = Field(default_factory=dict)
    dedup_overlap: dict[str, float] = Field(default_factory=dict)
    notes: str = ""

    def dominant_source(self) -> str | None:
        if not self.proportions:
            return None
        return max(self.proportions, key=lambda k: self.proportions[k])

    def balance_score(self) -> float:
        """1.0 = perfectly balanced, 0.0 = single source dominates."""
        if len(self.proportions) <= 1:
            return 0.0
        n = len(self.proportions)
        entropy = -sum(p * math.log(p) for p in self.proportions.values() if p > 0)
        max_entropy = math.log(n)
        return entropy / max_entropy if max_entropy > 0 else 0.0
