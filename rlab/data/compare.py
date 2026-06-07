from collections.abc import Mapping
from typing import Any


def compare_profiles(profiles: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics = sorted({key for profile in profiles.values() for key in profile})
    return {
        metric: {name: profile.get(metric) for name, profile in profiles.items()}
        for metric in metrics
    }
