"""Descubrimiento de funciones. Cada funcion es una carpeta skills/<nombre>/ con un feature.json:

  {"name": "shorts", "summary": "...", "requirements": "requirements.txt",
   "imports": ["modulo", ...],
   "tools": {"required": ["ffmpeg"], "optional": {"node": "para que sirve"}},
   "models": [{"name": "x.task", "url": "...", "required": true, "purpose": "..."}]}

y su codigo en src/mkyt_<nombre>/commands/<orden>.py (una orden por archivo, ejecutable con -m).
Para anadir una funcion basta con crear esa carpeta: el nucleo no se toca.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    name: str
    url: str
    required: bool = True
    purpose: str = ""


@dataclass(frozen=True)
class Feature:
    name: str
    root: Path
    summary: str = ""
    requirements: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    tools_required: tuple[str, ...] = ()
    tools_optional: dict = field(default_factory=dict)
    models: tuple[ModelSpec, ...] = ()

    @property
    def package(self) -> str:
        return f"mkyt_{self.name}"

    @property
    def src(self) -> Path:
        return self.root / "src"

    def commands(self) -> list[str]:
        folder = self.src / self.package / "commands"
        return sorted(p.stem for p in folder.glob("*.py") if not p.name.startswith("_"))

    def module_for(self, command: str) -> str:
        return f"{self.package}.commands.{command}"


def _load(root: Path) -> Feature:
    spec = json.loads((root / "feature.json").read_text(encoding="utf-8"))
    req_file = root / spec["requirements"] if spec.get("requirements") else None
    requirements = ()
    if req_file and req_file.exists():
        requirements = tuple(l.strip() for l in req_file.read_text(encoding="utf-8").splitlines()
                             if l.strip() and not l.startswith("#"))
    tools = spec.get("tools", {})
    return Feature(
        name=spec["name"], root=root, summary=spec.get("summary", ""), requirements=requirements,
        imports=tuple(spec.get("imports", [])), tools_required=tuple(tools.get("required", [])),
        tools_optional=dict(tools.get("optional", {})),
        models=tuple(ModelSpec(**m) for m in spec.get("models", [])),
    )


def discover(features_dir: Path) -> dict[str, Feature]:
    found = {}
    for manifest in sorted(features_dir.glob("*/feature.json")):
        feature = _load(manifest.parent)
        found[feature.name] = feature
    return found
