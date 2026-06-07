import json
from pathlib import Path

from rlab.context.environment import environment_snapshot


def environment_diff(run_dir: Path) -> dict[str, tuple[object, object]]:
    recorded_path = run_dir / "reproducibility" / "env.json"
    if not recorded_path.exists():
        return {}
    recorded = json.loads(recorded_path.read_text())
    current = environment_snapshot()
    return {
        key: (recorded.get(key), current.get(key))
        for key in ("python", "executable", "platform")
        if recorded.get(key) != current.get(key)
    }
