#!/usr/bin/env python3
"""Maintain the supported stable Godot image versions (Python standard library only)."""

import argparse
import json
import os
from pathlib import Path
import re
import urllib.request

CATALOG = Path(__file__).resolve().parents[1] / "godot-versions.json"
RELEASES = "https://api.github.com/repos/godotengine/godot-builds/releases"


def version_key(version):
    match = re.fullmatch(r"4\.(\d+)(?:\.(\d+))?-stable", version)
    if not match:
        raise ValueError(f"Unsupported stable Godot 4 version: {version!r}")
    return (4, int(match[1]), int(match[2] or 0))


def read_catalog(path=CATALOG):
    versions = json.loads(path.read_text())
    if not isinstance(versions, list) or not versions:
        raise ValueError("The version catalog must be a nonempty list")
    keys = [version_key(version) for version in versions]
    if len(set(keys)) != len(keys) or keys != sorted(keys):
        raise ValueError("The version catalog must be unique and sorted numerically")
    return versions


def fetch_releases():
    """Read every page: beta/dev releases can push stable entries off page one."""
    releases = []
    page = 1
    while True:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "godot-image-updater"}
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(f"{RELEASES}?per_page=100&page={page}", headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("Expected a GitHub releases array")
        releases.extend(batch)
        if len(batch) < 100:
            return releases
        page += 1


def missing_releases(versions, releases):
    """Include intermediate releases and late patches, starting at our baseline."""
    known = {version_key(version) for version in versions}
    minimum = min(known)
    missing = {}
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or release.get("prerelease"):
            continue
        if not re.fullmatch(r"4\.\d+(?:\.\d+)?-stable", tag):
            continue
        key = version_key(tag)
        if key < minimum or key in known:
            continue
        required = {
            f"Godot_v{tag}_linux.x86_64.zip",
            f"Godot_v{tag}_linux.arm64.zip",
            f"Godot_v{tag}_export_templates.tpz",
        }
        assets = {asset["name"] for asset in release.get("assets", [])}
        if absent := required - assets:
            raise ValueError(f"{tag} is missing required assets: {', '.join(sorted(absent))}")
        missing[tag] = release
    return [missing[tag] for tag in sorted(missing, key=version_key)]


def update_catalog(path, releases, body_path):
    versions = read_catalog(path)
    additions = missing_releases(versions, releases)
    if not additions:
        body_path.write_text("No new supported stable Godot releases.\n")
        print("No new supported stable Godot releases.")
        return
    updated = sorted(versions + [release["tag_name"] for release in additions], key=version_key)
    lines = [
        "Add the following official stable Godot releases to the image catalog.",
        "",
        "| Version | Release notes | Downloads | Changelog |",
        "| --- | --- | --- | --- |",
    ]
    for release in additions:
        tag = release["tag_name"]
        number = tag.removesuffix("-stable")
        lines.append(
            f"| {tag} | [Official release](https://github.com/godotengine/godot-builds/releases/tag/{tag}) "
            f"| [Archive](https://godotengine.org/download/archive/{tag}/) "
            f"| [Changes](https://godotengine.github.io/godot-interactive-changelog/#{number}) |"
        )
    lines += [
        "",
        f"After merge, publish exact version tags for linux/amd64 and linux/arm64; "
        f"promote `latest` to `{updated[-1]}` only after every build succeeds.",
        "",
        "Existing consumers stay on their pinned version/digest until upgraded separately.",
        "",
        "The weekly check validates required upstream assets. Bot-created PRs use GITHUB_TOKEN, "
        "and their PR workflows may need approval. The release check explicitly dispatches "
        "Build and publish on `automation/godot-stable` "
        "to validate both architectures without pushing. Check that workflow run before merging. "
        "Main builds and publication run after merge.",
    ]
    # Write only after all releases have passed validation.
    body_path.write_text("\n".join(lines) + "\n")
    path.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"Added {', '.join(release['tag_name'] for release in additions)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["latest", "matrix", "update"])
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--version", default="", help="Select one catalog version for a manual build")
    parser.add_argument("--releases-file", type=Path, help="Use a saved GitHub releases array")
    parser.add_argument("--body-file", type=Path, default=Path(".builds/godot-update.md"))
    args = parser.parse_args()
    versions = read_catalog(args.catalog)
    if args.command == "latest":
        print(versions[-1])
    elif args.command == "matrix":
        if args.version and args.version not in versions:
            parser.error("--version must be present in godot-versions.json")
        print(json.dumps(args.version and [args.version] or versions))
    else:
        releases = json.loads(args.releases_file.read_text()) if args.releases_file else fetch_releases()
        args.body_file.parent.mkdir(parents=True, exist_ok=True)
        update_catalog(args.catalog, releases, args.body_file)


if __name__ == "__main__":
    main()
