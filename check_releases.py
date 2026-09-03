#!/usr/bin/env python3
"""Check local release.json against anomalyco/opencode GitHub releases.
Verifies checksums, handles errors, avoids duplicate loops."""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

LOCAL_RELEASE = "release.json"
REPO = "anomalyco/opencode"
API_URL = f"https://api.github.com/repos/{REPO}/releases"


def fetch_releases():
    req = urllib.request.Request(
        API_URL + "?per_page=100",
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "check_releases/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"HTTP error fetching releases: {e.code} {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error fetching releases: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error fetching releases: {e}")
        sys.exit(1)


def main():
    # Load local release.json
    try:
        with open(LOCAL_RELEASE, "r", encoding="utf-8") as f:
            local = json.load(f)
    except FileNotFoundError:
        print(f"Local release file not found: {LOCAL_RELEASE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {LOCAL_RELEASE}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {LOCAL_RELEASE}: {e}")
        sys.exit(1)

    tag = local.get("tag_name")
    if not tag:
        print("Local release.json is missing 'tag_name'")
        sys.exit(1)

    # Fetch remote releases (single loop, no duplicates)
    releases = fetch_releases()
    remote_release = None
    for r in releases:
        if r.get("tag_name") == tag:
            remote_release = r
            break

    if remote_release is None:
        print(f"Release {tag} not found in {REPO}")
        sys.exit(1)

    print(f"Matched remote release: {tag} — {remote_release.get('name', 'N/A')}")

    # Find checksums.txt asset (single pass over assets)
    checksums = {}
    checksum_url = None
    for asset in remote_release.get("assets", []):
        name = asset.get("name", "")
        if name.lower() == "checksums.txt":
            checksum_url = asset.get("browser_download_url")
            break

    if checksum_url:
        try:
            with urllib.request.urlopen(checksum_url, timeout=30) as resp:
                for raw_line in resp.read().decode("utf-8", errors="ignore").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or line.startswith(" "):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        digest, filename = parts[0], parts[1].strip()
                        checksums[filename] = digest.lower()
        except urllib.error.HTTPError as e:
            print(f"HTTP error fetching checksums: {e.code}")
        except urllib.error.URLError as e:
            print(f"Network error fetching checksums: {e.reason}")
        except Exception as e:
            print(f"Error fetching checksums: {e}")
    else:
        print("Warning: checksums.txt not found in remote assets.")

    if checksums:
        print(f"Checksums loaded: {len(checksums)} file(s)")
        verified = 0
        mismatched = 0
        missing = 0
        for filename, expected in checksums.items():
            if not os.path.isfile(filename):
                print(f"  MISSING (expected checksum {expected}): {filename}")
                missing += 1
                continue
            try:
                with open(filename, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
                if digest == expected:
                    print(f"  OK: {filename} ({expected})")
                    verified += 1
                else:
                    print(f"  MISMATCH: {filename} expected={expected} got={digest}")
                    mismatched += 1
            except Exception as e:
                print(f"  ERROR reading {filename}: {e}")
        print(f"Verification complete: {verified} OK, {mismatched} mismatch, {missing} missing")
    else:
        print("No checksums to verify.")

    # Compare asset lists (single loops over each list — not duplicate)
    remote_assets = {a.get("name") for a in remote_release.get("assets", []) if a.get("name")}
    local_assets = {a.get("name") for a in local.get("assets", []) if a.get("name")}
    only_remote = remote_assets - local_assets
    only_local = local_assets - remote_assets
    if only_remote:
        print(f"Assets only on remote ({REPO}): {only_remote}")
    if only_local:
        print(f"Assets only locally: {only_local}")
    if not only_remote and not only_local:
        print("Asset names match between local and remote.")


if __name__ == "__main__":
    main()
