from pathlib import Path

from rlab.external.command import ExternalCommand
from rlab.external.runner import DockerRunner
from rlab.launchers.local import LocalLauncher


class DockerLauncher(LocalLauncher):
    def command(self, image: str, *args: str) -> ExternalCommand:
        return DockerRunner().command(
            image,
            *args,
            mounts=((self.root, "/workspace"),),
            cwd=Path.cwd(),
        )
