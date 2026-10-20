"""
Role Registry — convention-based plugin loader.

A role is a Python module or package dropped into:

    app/agents/role_tools/

It MUST export:

    ROLE_MANIFEST : dict
        required keys: role_id, name

It MAY export:

    ROLE_TOOLS : list
        @tool-decorated callables

    ROLE_HOOKS : dict
        optional lifecycle hooks:
          on_init
          pre_process
          post_process
          augment_user_content
          build_rag_filter

The framework does NOT know any role by name. It scans role_tools/,
loads every importable module, reads the exported attributes, and
caches RoleContext objects.

Adding a role = dropping a module/package + restart.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

ROLE_DIR = Path(__file__).parent / "role_tools"


DEFAULT_MEMORY_POLICY = {
    "scope": "isolated",
    "include_global": False,
    "include_default_role": False,
    "allow_learning": True,
}


@dataclass
class RoleContext:
    role_id: str
    name: str

    system_prompt: str = ""
    citation_mode: str = "rag"
    model_override: Optional[str] = None
    runtime_profile: Optional[str] = None

    memory_policy: Dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_MEMORY_POLICY)
    )

    tools: List[Any] = field(default_factory=list)
    rag_collections: List[str] = field(default_factory=list)
    rag_top_k: int = 12

    output_subdir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    hooks: Dict[str, Callable[..., Any]] = field(default_factory=dict)

    module_name: Optional[str] = None
    package_dir: Optional[Path] = None

    @property
    def tool_names(self) -> List[str]:
        return [getattr(t, "name", str(t)) for t in self.tools]

    @property
    def has_tools(self) -> bool:
        return bool(self.tools)

    def hook(self, name: str) -> Optional[Callable[..., Any]]:
        fn = self.hooks.get(name)
        return fn if callable(fn) else None

    def output_path(self, root: Optional[Path] = None) -> Optional[Path]:
        if not self.output_subdir:
            return None
        base = (
            root or Path(__file__).resolve().parents[2] / "workspace"
        )  # MAI-PATCH agent_core.py v1
        return base / self.output_subdir


class RoleRegistry:
    def __init__(self) -> None:
        self._packages: Dict[str, Dict[str, Any]] = {}
        self._discover()

    def _discover(self) -> None:
        self._packages.clear()

        if not ROLE_DIR.exists():
            logger.warning("Role directory missing: %s", ROLE_DIR)
            return

        for entry in sorted(ROLE_DIR.iterdir()):
            try:
                if entry.name.startswith("__"):
                    continue

                if entry.is_file() and entry.suffix != ".py":
                    continue

                if entry.is_dir() and not (entry / "__init__.py").exists():
                    continue

                module_name = entry.stem if entry.is_file() else entry.name
                full_module = f"app.agents.role_tools.{module_name}"

                try:
                    mod = importlib.import_module(full_module)
                except Exception as exc:
                    logger.warning(
                        "Could not import role module %s: %s",
                        full_module,
                        exc,
                    )
                    continue

                manifest = getattr(mod, "ROLE_MANIFEST", None)

                if not isinstance(manifest, dict) or "role_id" not in manifest:
                    logger.debug("Skipped %s: no valid ROLE_MANIFEST", full_module)
                    continue

                role_id = str(manifest["role_id"])

                self._packages[role_id] = {
                    "module": mod,
                    "module_name": full_module,
                    "manifest": manifest,
                    "tools": list(getattr(mod, "ROLE_TOOLS", []) or []),
                    "hooks": dict(getattr(mod, "ROLE_HOOKS", {}) or {}),
                    "package_dir": entry if entry.is_dir() else entry.parent,
                }

                logger.info("Discovered role package: %s (%s)", role_id, full_module)

            except Exception as exc:
                logger.warning("Role discovery error for %s: %s", entry, exc)

    def reload(self) -> None:
        self._discover()

    def list_roles(self) -> List[str]:
        return sorted(self._packages.keys())

    def get(self, role_id: Optional[str]) -> Optional[RoleContext]:
        if not role_id:
            return None

        pkg = self._packages.get(role_id)
        if not pkg:
            return None

        manifest = pkg["manifest"]

        memory_policy = dict(DEFAULT_MEMORY_POLICY)
        memory_policy.update(manifest.get("memory_policy", {}) or {})

        return RoleContext(
            role_id=role_id,
            name=str(manifest.get("name", role_id)),
            system_prompt=str(manifest.get("system_prompt", "") or ""),
            citation_mode=str(manifest.get("citation_mode", "rag")),
            model_override=manifest.get("model_override"),
            runtime_profile=manifest.get("runtime_profile"),
            memory_policy=memory_policy,
            tools=list(pkg["tools"]),
            rag_collections=list(manifest.get("rag_collections", []) or []),
            rag_top_k=int(manifest.get("rag_top_k", 12) or 12),
            output_subdir=manifest.get("output_subdir"),
            metadata=dict(manifest.get("metadata", {}) or {}),
            hooks=dict(pkg["hooks"]),
            module_name=pkg["module_name"],
            package_dir=pkg["package_dir"],
        )


_registry: Optional[RoleRegistry] = None


def get_registry() -> RoleRegistry:
    global _registry
    if _registry is None:
        _registry = RoleRegistry()
    return _registry


def tools_for_role(role_ctx: Optional[RoleContext], core_tools: List[Any]) -> List[Any]:
    """
    Return core tools plus role-specific tools.

    Duplicate tool names are avoided. Role tools are appended after core tools.
    """

    core = list(core_tools or [])

    if role_ctx is None:
        return core

    core_names = {getattr(t, "name", None) for t in core}
    role_tools = [
        t for t in role_ctx.tools if getattr(t, "name", None) not in core_names
    ]

    return core + role_tools
