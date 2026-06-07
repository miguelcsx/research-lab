import os
import platform
import sys
from collections.abc import Mapping


def environment_snapshot() -> Mapping[str, object]:
    return {
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "variables": {
            key: value
            for key, value in os.environ.items()
            if key.startswith(("CUDA_", "PYTHON", "SLURM_", "RLAB_"))
        },
    }
