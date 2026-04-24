from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(slots=True)
class ArtifactSync:
    mode: str
    target: str

    def sync(self, export_dir: Path) -> None:
        if not self.target:
            return

        if self.mode == "local":
            destination = Path(self.target)
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(export_dir, destination)
            return

        if self.mode == "scp":
            subprocess.run(
                ["scp", "-r", str(export_dir), self.target],
                check=True,
            )
            return

        raise ValueError(f"Unsupported sync mode: {self.mode}")

