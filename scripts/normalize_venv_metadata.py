#!/usr/bin/env python3
"""Remove uv's per-build cache timestamp from the installed app metadata."""

from __future__ import annotations

import argparse
from pathlib import Path


def normalize_venv_metadata(venv: Path) -> None:
    site_packages = venv / "lib/python3.12/site-packages"
    dist_info_dirs = list(site_packages.glob("percival_osm-*.dist-info"))
    if len(dist_info_dirs) != 1:
        raise RuntimeError(
            f"Expected one percival_osm dist-info directory, found {len(dist_info_dirs)}"
        )

    dist_info = dist_info_dirs[0]
    uv_cache = dist_info / "uv_cache.json"
    record = dist_info / "RECORD"
    if not uv_cache.exists():
        return
    if not record.is_file():
        raise RuntimeError(f"Missing package RECORD file: {record}")

    record_lines = record.read_text(encoding="utf-8").splitlines()
    record_lines = [
        line for line in record_lines
        if not line.startswith(f"{dist_info.name}/uv_cache.json,")
    ]
    uv_cache.unlink()
    record.write_text("\n".join(record_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("venv", type=Path)
    args = parser.parse_args()
    normalize_venv_metadata(args.venv)


if __name__ == "__main__":
    main()
