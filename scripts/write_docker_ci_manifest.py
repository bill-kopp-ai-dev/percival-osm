"""Write non-secret source and image metadata for a local CI build."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dockerfile", type=Path, default=Path("Dockerfile"))
    parser.add_argument("--lock", type=Path, action="append")
    args = parser.parse_args()
    raw = subprocess.check_output(["docker", "image", "inspect", args.image], text=True)
    image = json.loads(raw)[0]
    labels = image.get("Config", {}).get("Labels", {})
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.source_sha) is None:
        raise SystemExit("source SHA must be a full 40- or 64-character Git object ID")
    if f"{image['Os']}/{image['Architecture']}" != "linux/amd64":
        raise SystemExit("CI image platform is not the approved linux/amd64 target")
    if labels.get("org.opencontainers.image.revision") != args.source_sha:
        raise SystemExit(
            "image revision label does not match the checked-out source SHA"
        )
    if labels.get("org.opencontainers.image.version") in (
        None,
        "0.0.0",
        "unknown",
        "local",
    ):
        raise SystemExit("image version label is missing or a placeholder")
    base_images = [
        fields[1]
        for line in args.dockerfile.read_text(encoding="utf-8").splitlines()
        if (fields := line.split()) and fields[0].upper() == "FROM" and len(fields) >= 2
    ]
    if not base_images or any(
        re.search(r"@sha256:[0-9a-f]{64}$", image) is None for image in base_images
    ):
        raise SystemExit(f"Dockerfile contains an unpinned base image: {base_images}")
    lock_digests: dict[str, str] = {}
    for lock_path in args.lock or [Path("uv.lock")]:
        if not lock_path.exists():
            raise SystemExit(f"dependency lock input does not exist: {lock_path}")
        digest = hashlib.sha256()
        files = (
            sorted(path for path in lock_path.rglob("*") if path.is_file())
            if lock_path.is_dir()
            else [lock_path]
        )
        if not files:
            raise SystemExit(f"dependency lock directory is empty: {lock_path}")
        for file_path in files:
            relative = (
                file_path.relative_to(lock_path)
                if lock_path.is_dir()
                else Path(file_path.name)
            )
            digest.update(relative.as_posix().encode("utf-8") + b"\0")
            digest.update(file_path.read_bytes())
        lock_digests[lock_path.as_posix()] = digest.hexdigest()
    payload = {
        "source_sha": args.source_sha,
        "image": args.image,
        "image_id": image["Id"],
        "repo_digests": image.get("RepoDigests", []),
        "platform": f"{image['Os']}/{image['Architecture']}",
        "base_images": base_images,
        "version": labels.get("org.opencontainers.image.version"),
        "revision": labels.get("org.opencontainers.image.revision"),
        "dependency_locks_sha256": lock_digests,
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
