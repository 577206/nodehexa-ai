#!/usr/bin/env python3
"""build123d source for this model project.

Replace the starter geometry with model-specific construction. Keep the project
spec and parameters as the authoring contract. Running this file directly is a
build smoke check; export STEP only through scripts/export_step.py after review
confirmation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_ROOT / "review" / "cache"))


def load_parameters(path: Path) -> dict:
    """Load the project parameter document from YAML."""

    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to read parameters.yaml. "
            "Run scripts/check_environment.py --install with this Python runtime."
        ) from exc

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"missing parameters file: {path}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("parameters.yaml must contain a YAML mapping")
    if not isinstance(data.get("parameters"), dict):
        raise RuntimeError("parameters.yaml must contain a 'parameters' mapping")
    return data


def parameter_value(params: dict, parameter_id: str, default: float) -> float:
    """Return a positive numeric parameter value from the project document."""

    parameters = params.get("parameters", {})
    entry: Any = parameters.get(parameter_id, default) if isinstance(parameters, dict) else default
    value = entry.get("value", default) if isinstance(entry, dict) else entry
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"parameter {parameter_id} must be numeric")
    value = float(value)
    if value <= 0:
        raise RuntimeError(f"parameter {parameter_id} must be positive")
    return value


def build_model(params: dict):
    """Build and return a build123d Part or Assembly.

    Implement model-specific geometry here. Keep major features in named helper
    functions so review refs and validation checks remain traceable.
    """

    raise RuntimeError("Cover CAD intentionally not generated: electronics envelope and screw seat details must be confirmed first. See spec/current.yaml open_questions.")


def write_step(model, path: Path) -> None:
    from build123d import export_step as build123d_export_step

    path.parent.mkdir(parents=True, exist_ok=True)
    build123d_export_step(model, str(path))


def model_summary(model) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": type(model).__name__}
    bounding_box = getattr(model, "bounding_box", None)
    if callable(bounding_box):
        try:
            box = bounding_box()
            summary["bbox_size"] = [
                float(getattr(box.size, "X")),
                float(getattr(box.size, "Y")),
                float(getattr(box.size, "Z")),
            ]
        except Exception:
            pass
    return summary


def main() -> None:
    params = load_parameters(PROJECT_ROOT / "parameters.yaml")
    model = build_model(params)
    print("built source/model.py successfully; STEP export is deferred to scripts/export_step.py")
    print(model_summary(model))


if __name__ == "__main__":
    main()
