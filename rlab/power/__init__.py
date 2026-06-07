import math
from pydantic import BaseModel, ConfigDict


class BudgetEstimate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_jobs: int
    estimated_gpu_hours: float = 0.0
    estimated_wall_hours: float = 0.0
    estimated_storage_gb: float = 0.0
    estimated_cost_usd: float | None = None
    notes: str = ""


def estimate_required_repetitions(
    effect_size: float,
    observed_variance: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Estimate minimum repetitions to detect `effect_size` with `power`.

    Uses a simple normal approximation for two-sample t-test.
    """
    if effect_size <= 0 or observed_variance <= 0:
        return 1
    # Z-scores for alpha/2 (two-sided) and 1-beta
    z_alpha = _z_score(1 - alpha / 2)
    z_beta = _z_score(power)
    n = 2 * observed_variance * ((z_alpha + z_beta) ** 2) / (effect_size ** 2)
    return max(1, math.ceil(n))


def estimate_budget(
    total_jobs: int,
    *,
    seconds_per_job: float = 3600.0,
    gpus_per_job: float = 0.0,
    storage_gb_per_job: float = 1.0,
    gpu_hour_cost_usd: float | None = None,
) -> BudgetEstimate:
    wall_hours = total_jobs * seconds_per_job / 3600
    gpu_hours = total_jobs * gpus_per_job * seconds_per_job / 3600
    storage = total_jobs * storage_gb_per_job
    cost = gpu_hours * gpu_hour_cost_usd if gpu_hour_cost_usd is not None else None
    return BudgetEstimate(
        total_jobs=total_jobs,
        estimated_gpu_hours=gpu_hours,
        estimated_wall_hours=wall_hours,
        estimated_storage_gb=storage,
        estimated_cost_usd=cost,
    )


def _z_score(p: float) -> float:
    """Inverse normal CDF using rational approximation (Abramowitz & Stegun 26.2.17)."""
    if p <= 0:
        return -1e10
    if p >= 1:
        return 1e10
    if p < 0.5:
        return -_z_score(1 - p)
    t = math.sqrt(-2 * math.log(1 - p))
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)
    return t - (c[0] + c[1] * t + c[2] * t**2) / (1 + d[0] * t + d[1] * t**2 + d[2] * t**3)


__all__ = ["BudgetEstimate", "estimate_budget", "estimate_required_repetitions"]
