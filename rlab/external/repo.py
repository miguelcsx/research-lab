import subprocess
from pathlib import Path

from rlab.errors import ExternalRunError


def checkout_repository(url: str, revision: str, cache_root: Path) -> Path:
    destination = cache_root / revision
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        clone = subprocess.run(
            ("git", "clone", "--no-checkout", url, str(destination)),
            text=True,
            capture_output=True,
            check=False,
        )
        if clone.returncode:
            raise ExternalRunError(clone.stderr.strip())
    checkout = subprocess.run(
        ("git", "checkout", "--detach", revision),
        cwd=destination,
        text=True,
        capture_output=True,
        check=False,
    )
    if checkout.returncode:
        raise ExternalRunError(checkout.stderr.strip())
    return destination
