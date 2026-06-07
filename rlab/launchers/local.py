from pathlib import Path

from rlab.external.command import ExternalCommand
from rlab.external.runner import CommandResult, ShellRunner


class LocalLauncher:
    def __init__(self, root: Path) -> None:
        self.root = root

    def launch(self, command: ExternalCommand) -> CommandResult:
        return ShellRunner().run(command, self.root)
