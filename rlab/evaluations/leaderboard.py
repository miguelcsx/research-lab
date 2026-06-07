from collections.abc import Iterable

from rlab.evaluations.result import EvaluationResult, LeaderboardResult


def leaderboard(suite: str, results: Iterable[EvaluationResult]) -> LeaderboardResult:
    models: dict[str, dict[str, float]] = {}
    for result in results:
        models[result.model] = {
            f"{task.task}.{name}": value
            for task in result.tasks
            for name, value in task.metrics.items()
        }
    return LeaderboardResult(suite=suite, models=models)
