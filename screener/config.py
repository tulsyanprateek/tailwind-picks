"""Load config.yaml and resolve paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

_PATH_KEYS = ("output_dir", "data_dir", "cache_dir", "log_dir")


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    # The cloud run (GitHub Actions) writes into its own folder.
    if os.environ.get("SCREENER_OUTPUT_DIR"):
        cfg["paths"]["output_dir"] = os.environ["SCREENER_OUTPUT_DIR"]
    for key in _PATH_KEYS:
        p = Path(str(cfg["paths"][key])).expanduser()
        if not p.is_absolute():
            p = ROOT / p
        cfg["paths"][key] = p
    cfg["relative_strength"]["weights"] = {int(k): float(v)
                                           for k, v in cfg["relative_strength"]["weights"].items()}
    return cfg
