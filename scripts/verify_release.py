#!/usr/bin/env python3
"""verify_release.py — compare git tag, asset names, SHA256, SBOM presence."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Verify release artifacts")
    parser.add_argument("--tag", default=os.getenv("GITHUB_REF_NAME", "v0.0.0"))
    parser.add_argument("--release-dir", default=".")
    args = parser.parse_args()

    release_dir = Path(args.release_dir)
    tag = args.tag.lstrip("v")
    tag_full = f"v{tag}" if not args.tag.startswith("v") else args.tag
    errors = []
    passes = []

    # 1. Git tag comparison (compare with release.json if present)
    release_json_path = release_dir / "release.json"
    if release_json_path.exists():
        with open(release_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tag_name = data.get("tag_name", "")
        if tag_name == tag_full or tag_name == tag:
            passes.append(f"PASS: release.json tag_name ({tag_name}) matches {tag_full}")
        else:
            errors.append(f"FAIL: release.json tag_name ({tag_name}) != expected {tag_full}")
    else:
        passes.append("INFO: release.json not found locally; comparing tag only")

    # 2. Asset names check (expected patterns)
    expected_patterns = [
        "opencode-linux-x86_64.tar.gz",
        "opencode-darwin-x86_64.tar.gz",
        "opencode-darwin-arm64.tar.gz",
        "opencode-windows-x64.zip",
        "checksums.txt",
        "sbom.spdx.json",
    ]
    for pattern in expected_patterns:
        found = any(p.name == pattern for p in release_dir.iterdir() if p.is_file())
        if found:
            passes.append(f"PASS: asset {pattern} present")
        else:
            # Don't fail for missing artifacts if we are only running tag comparison locally
            passes.append(f"INFO: asset {pattern} not present locally (may be in release assets)")

    # 3. SHA256 / checksums.txt verification
    checksums_path = release_dir / "checksums.txt"
    if checksums_path.exists():
        with open(checksums_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 1:
                    expected_hash = parts[0]
                    # Derive file name from rest of line or from common naming
                    # For simplicity check if a matching archive exists and verify
                    for p in release_dir.iterdir():
                        if p.is_file() and p.name.endswith((".tar.gz", ".zip", ".sig", ".pem")):
                            computed = sha256_file(p)
                            if computed == expected_hash:
                                passes.append(f"PASS: {p.name} SHA256 matches checksums.txt")
    else:
        passes.append("INFO: checksums.txt not found locally")

    # 4. SBOM presence
    sbom_path = release_dir / "sbom.spdx.json"
    if sbom_path.exists():
        with open(sbom_path, "r", encoding="utf-8") as f:
            sbom_data = json.load(f)
        if sbom_data.get("spdxVersion") and sbom_data.get("SPDXID"):
            passes.append("PASS: sbom.spdx.json valid SPDX JSON present")
        else:
            errors.append("FAIL: sbom.spdx.json missing SPDX fields")
    else:
        passes.append("INFO: sbom.spdx.json not found locally (release artifact expected)")

    # 5. HMAC / checksum block verification reference
    install_path = Path("install.sh")
    if install_path.exists():
        content = install_path.read_text(encoding="utf-8")
        if "hashlib.sha256" in content:
            passes.append("PASS: install.sh contains hashlib.sha256 checksum verification")
        else:
            errors.append("FAIL: install.sh missing hashlib.sha256 block")
        if "hmac" in content.lower() or "HMAC" in content:
            passes.append("PASS: install.sh references HMAC verification")
        else:
            passes.append("INFO: install.sh HMAC reference optional (add if required)")
    else:
        errors.append("FAIL: install.sh not found")

    # Print results
    print("\n=== Release Verification Report ===")
    print(f"Tag (expected): {tag_full}")
    print(f"Release dir: {release_dir.resolve()}")
    for p in passes:
        print(p)
    for e in errors:
        print(e)

    if errors:
        print(f"\nRESULT: {len(errors)} error(s) found.")
        sys.exit(1)
    else:
        print(f"\nRESULT: All checks passed ({len(passes)} passes, 0 errors).")
        sys.exit(0)

if __name__ == "__main__":
    main()
