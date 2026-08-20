from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from pathlib import Path

from .models import QuiltProject, utc_now


def default_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "QuiltForge"


class ProjectStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else default_data_dir()
        self.projects_dir = self.root / "Projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _slug(name: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
        return value[:48] or "untitled"

    def folder_for(self, project: QuiltProject) -> Path:
        matches = list(self.projects_dir.glob(f"*-{project.id}"))
        if matches:
            return matches[0]
        return self.projects_dir / f"{self._slug(project.name)}-{project.id}"

    def create(self, name: str, source_path: str | Path) -> QuiltProject:
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        project = QuiltProject(id=uuid.uuid4().hex[:10], name=name.strip() or source.stem, source_image="")
        folder = self.folder_for(project)
        assets = folder / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        suffix = source.suffix.lower() if source.suffix else ".png"
        destination = assets / f"source{suffix}"
        shutil.copy2(source, destination)
        project.source_image = str(destination)
        self.save(project)
        return project

    def save(self, project: QuiltProject) -> Path:
        project.updated_at = utc_now()
        folder = self.folder_for(project)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "project.qforge"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
        temporary.replace(target)
        return target

    def load(self, path: str | Path) -> QuiltProject:
        target = Path(path)
        if target.is_dir():
            target = target / "project.qforge"
        data = json.loads(target.read_text(encoding="utf-8"))
        project = QuiltProject.from_dict(data)
        if not Path(project.source_image).is_absolute():
            project.source_image = str((target.parent / project.source_image).resolve())
        return project

    def recent(self, limit: int = 12) -> list[tuple[QuiltProject, Path]]:
        items: list[tuple[QuiltProject, Path]] = []
        for target in self.projects_dir.glob("*/project.qforge"):
            try:
                items.append((self.load(target), target))
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
        items.sort(key=lambda item: item[0].updated_at, reverse=True)
        return items[:limit]

    def delete(self, project: QuiltProject) -> None:
        folder = self.folder_for(project)
        if folder.parent.resolve() != self.projects_dir.resolve():
            raise ValueError("Refusing to delete outside the QuiltForge project library")
        if folder.exists():
            shutil.rmtree(folder)

