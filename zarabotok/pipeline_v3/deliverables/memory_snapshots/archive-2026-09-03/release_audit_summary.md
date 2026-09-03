# BuildReleaseAuditor — Release & Build Integrity Audit
**Agent:** BuildReleaseAuditor  
**Workspace:** C:\Users\klass\OneDrive\Desktop\work  
**Audit date:** 2026-08-31  
**Scope:** release.json, check_releases.py, opencode-src/ (main.go, go.mod, README.md, .opencode.json, install, .goreleaser.yml, .github/workflows), install.sh (root), opencode.exe, .opencode/ config

---

## 1. Inspected Artifacts (evidence paths)
| File | Size / Lines | Key facts |
|---|---|---|
| `release.json` | ~16.7 KB (1 release dict) | Single release `v0.0.55` (tag `v0.0.55`, id 228252352), published 2025-06-27T06:51:34Z, draft=false, prerelease=false. 9 assets. Author `kujtimiihoxha` (id 14311743). Body length 94 chars. |
| `check_releases.py` | 522 B / 18 lines | Fetches `https://api.github.com/repos/opencode-ai/opencode/releases`, prints first 10 releases, filters asset names by substring `windows` \| `amd64` \| `x86_64`. Uses `urllib.request.Request` with `Accept: application/vnd.github.v3+json`. No checksums, no SSL hardening, no local comparison. |
| `opencode-src/main.go` | 284 B / 11 lines | Minimal wrapper: imports `cmd`, calls `cmd.Execute()`, defers `logging.RecoverPanic`. |
| `opencode-src/go.mod` | 6.3 KB / ~90 lines | Module `github.com/opencode-ai/opencode`, `go 1.24.0`. Direct deps include Azure SDK (`azidentity`), Anthropic SDK (`anthropic-sdk-go`), OpenAI (`openai-go` v0.1.0-beta.2), Bubble Tea, Cobra, Viper, SQLite3 (`ncruces/go-sqlite3`), Goose ORM. `go.sum` present (33 KB). |
| `opencode-src/README.md` | 25 KB / 400+ lines | **Archived.** Project moved to `Crush` (`https://github.com/charmbracelet/crush`). Early-development warning. Install methods listed (install script, Homebrew, AUR, `go install`). No verification/checksum instructions. |
| `opencode-src/.opencode.json` | 112 B | `{"$schema":"./opencode-schema.json","lsp":{"gopls":{"command":"gopls"}}}` — no secrets, no API keys. |
| `opencode-src/install` | 5.1 KB / ~150 lines | Bash installer (correct repo `github.com/opencode-ai/opencode`). Downloads `opencode-$os-$arch.tar.gz`. Has `check_version()` with **hardcoded `installed_version="0.0.1"`** (line ~77) and TODO comment `## TODO: check if version is installed`. No checksum/download verification. Adds to `PATH` via shell config. |
| `opencode-src/.goreleaser.yml` | 1.9 KB / ~100 lines | `version: 2`. Builds `linux` + `darwin` (`amd64` + `arm64`), `CGO_ENABLED=0`. Archives `tar.gz` with templated names (`opencode-linux-...`, `mac-...`). `checksum: name_template: "checksums.txt"`. `changelog` filter excludes docs/test/ci. `nfpms`: `deb` + `rpm`. `brews`: `opencode-ai/homebrew-tap`. `aurs`: `opencode-ai-bin` with `private_key: "{{ .Env.AUR_KEY }}"`. **No `signs:` block** (no GPG / cosign / keyless). **No `sbom:` block**. **No windows build** in `builds:` but archive overrides reference `windows` — inconsistency. |
| `.github/workflows/build.yml` | 718 B | `workflow_dispatch` + `push: main`. Uses `actions/checkout@v3`, `setup-go@v5`, `go mod download`, `goreleaser-action@v6` with `build --snapshot --clean`. No vulnerability scan, no SBOM, no artifact signing. |
| `.github/workflows/release.yml` | 830 B | `workflow_dispatch` + `push: tags: "*"`. Same steps + `release --clean`. Env: `GITHUB_TOKEN`, `AUR_KEY`. No signed release step, no checksum verification step, no SBOM generation, no `govulncheck` / `trivy`. |
| `install.sh` (work root) | 13.7 KB / ~350 lines | **Points to WRONG repo**: `https://github.com/anomalyco/opencode/releases/latest/download/$filename` (lines ~180, ~190) and `sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p'` for version extraction. Supports `linux-x64`, `linux-arm64`, `darwin-x64`, `darwin-arm64`, `windows-x64`, with `baseline` / `musl` variants. **No checksum verification of downloaded archive.** Only verifies HTTP 404 before download. Has `check_version()` (line ~250) that compares `opencode --version`; no HMAC or digest check. |
| `opencode-src/opencode.exe` | 61.6 MB (61,628,416 bytes) | Windows binary present locally. **Not signed** (`Get-AuthenticodeSignature`: `Status = NotSigned`). No version info embedded (`FileVersion`, `ProductVersion` empty). SHA-256: `162B4245CCDBCAB0335178EC92FFFC7DAF6361626D89C852F1BAB25084C01F6F`. Does not match any `release.json` asset digest (release has no Windows artifact — see below). |
| `opencode-src/scripts/release` | 1.2 KB | Bash tag-bumping script (`git tag $new_version`, `git push --tags`). No version validation, no checksum generation, no CI trigger. |
| `opencode-src/scripts/snapshot` | 82 B | Likely `goreleaser release --snapshot`. |
| `opencode-src/scripts/check_hidden_chars.sh` | 1.5 KB | Checks Go files for Unicode hidden chars (U+200B, U+202A-U+202E, BOM). Good supply-chain hygiene step, but not integrated into CI workflow (`build.yml` / `release.yml` do not call it). |
| `.opencode/` (work root) | directory with `node_modules/` | Plugin package `@opencode-ai/plugin@1.18.18`. No hardcoded secrets found in `package-lock.json` (searched for `sk-`, `AKIA`, `ghp_`, `AIza`, `eyJ`, `secret`, `token`). `package.json` clean. |

---

## 2. Release Process Integrity

### Versions & Tags
- `release.json` captures exactly one release: `v0.0.55` (tag `v0.0.55`).
- `.github/workflows/release.yml` triggers on tag push (`*`), using `goreleaser-action@v6` with `release --clean`.
- `scripts/release` manually bumps tags (`git tag $new_version; git push --tags`). No automated semver validation or changelog generation beyond `.goreleaser.yml`.
- **Gap:** No release notes automation from commit messages; `release.json` body is 94 chars (only one commit hash `4427df58...` and message `fixup early return for ollama (#266)`). Missing migration notes, breaking-change warnings, security advisories.

### Checksums & Artifacts
- `.goreleaser.yml` defines `checksum: name_template: "checksums.txt"`. `release.json` confirms `checksums.txt` exists (id 267762414, 738 B, sha256 `e3c606...`).
- All 9 assets have GitHub-computed `digest` fields (`sha256:...`) in `release.json` — integrity metadata is present at the API level.
- `release.json` assets: `checksums.txt`, `opencode-linux-amd64.{deb,rpm}`, `opencode-linux-arm64.{deb,rpm,tar.gz}`, `opencode-linux-x86_64.tar.gz`, `opencode-mac-arm64.tar.gz`, `opencode-mac-x86_64.tar.gz`.
- **Gap:** No Windows binary in release artifacts, yet `opencode.exe` exists locally (61 MB) and `install.sh` supports `windows-x64`. Either the Windows binary is built outside goreleaser or it is missing from releases — unverified origin.
- **Gap:** `checksums.txt` is plain text; no GPG detached signature (`checksums.txt.asc` missing), no Sigstore / cosign signature on artifacts or checksum file. User must manually download and verify digest against `release.json` — not practical.

### Changelogs
- `.goreleaser.yml` has `changelog:` with `sort: asc` and filters (`exclude: ^docs:`, `^test:`, `^ci:`, etc.). This is good.
- However `release.json` body is minimal. The project is **archived** (README states moved to Crush), so new releases are unlikely. The audit should treat `v0.0.55` as the final provenance artifact.

---

## 3. Build Errors / Missing Steps

### Errors in check_releases.py
- **Line 5:** `url = 'https://api.github.com/repos/opencode-ai/opencode/releases'` — correct repo, but no pagination (`?per_page=100` missing), so only first 30 releases returned by GitHub default; script prints only first 10.
- **Lines 8-10:** Filter logic `if 'windows' in name or 'amd64' in name or 'x86_64' in name:` is case-sensitive substring match; it will miss `arm64` or `mac` assets. It also prints `browser_download_url` only — no digest verification.
- **No error handling:** `urllib.request.urlopen` can raise `URLError`, `HTTPError`, `SSLError`; script will crash with traceback.
- **No comparison:** Does not read `release.json` or compare against expected asset list / digests.
- **No version check:** Does not verify that downloaded version matches tag.
- **No HMAC / checksum call:** No call to `hashlib.sha256` on downloaded files.

### Build / CI Gaps
- `build.yml` and `release.yml` use `actions/checkout@v3` (older version; `v4` available) and `setup-go@v5`. Not critical, but outdated.
- `go mod download` runs but `go mod verify` is missing (would verify module checksums in `go.sum`).
- No `go test` step in CI (only `build --snapshot`). No test coverage gate.
- `scripts/check_hidden_chars.sh` exists but is **not invoked** in CI — potential supply-chain injection vector (hidden Unicode chars in Go source) not checked automatically.
- `scripts/release` does not call `check_hidden_chars.sh` or `go test`.

### Install Script Issues
- `install.sh` (work root) references **wrong repository** (`anomalyco/opencode` instead of `opencode-ai/opencode`). If a user runs `curl -fsSL https://opencode.ai/install | bash`, they may download a different binary or a non-existent release.
- `install` (opencode-src) uses correct repo but has broken version check (`installed_version="0.0.1"`). If user installs `v0.0.55`, script thinks it is not installed and re-downloads every time (or exits incorrectly).
- Neither script verifies downloaded archive against `checksums.txt` or `release.json` digests.
- `install.sh` does not verify SSL certificate pinning or use `curl --cacert`; standard CA bundle used.

---

## 4. Strong Points

1. **Go modules & dependency tracking:** `go.mod` + `go.sum` present. Module path is canonical (`github.com/opencode-ai/opencode`). Dependencies pinned (e.g., `anthropic-sdk-go v1.4.0`, `openai-go v0.1.0-beta.2`).
2. **Existing `.goreleaser.yml`:** Professional release automation with multi-arch (`amd64`/`arm64`), multi-OS (`linux`/`darwin`), archives (`tar.gz`), package managers (`deb`/`rpm`), AUR, Homebrew tap, changelog filtering, checksum generation.
3. **`opencode.exe` binary present:** Windows build exists locally (though unverified origin). Binary is executable (`chmod 755` in install). Size ~62 MB consistent with Go binary + static linking (`CGO_ENABLED=0`).
4. **`install.sh` / `install` scripts:** Provide one-line install (`curl ... | bash`), support specific versions (`VERSION=...`), handle OS/arch detection (including `musl`, `baseline`, Rosetta on macOS), add to `PATH`, support `GITHUB_ACTIONS`. `install.sh` also supports `--binary` for offline/local installation.
5. **Hidden-character scanner:** `check_hidden_chars.sh` demonstrates awareness of Unicode prompt-injection vectors (zero-width spaces, bidi overrides, BOM).
6. **Release artifact diversity:** `release.json` shows 9 assets covering Linux amd64/arm64 (tar.gz + deb + rpm) and mac arm64/x86_64 (tar.gz). This is a broad deployment footprint.
7. **No hardcoded secrets in repo:** `internal/config/config.go` reads API keys from environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.). `.opencode.json` has only LSP config. `package-lock.json` clean.
8. **CI workflows exist:** `build.yml` and `release.yml` provide automation for snapshot builds and tagged releases.

---

## 5. Weak Points

1. **Errors in `check_releases.py`:** No pagination, wrong filter logic (misses arm64/mac), no digest verification, no error handling, prints only URLs.
2. **No tests for release:** No `test_check_releases.py`, `test_release_artifacts.py`, or `test_install.sh`. `.pytest_cache` present but no test files for release integrity.
3. **Unverified binary origin:** `opencode.exe` is **unsigned**, not in `release.json` assets, and its SHA-256 (`162B4245...`) is not cross-referenced with any release or build log. Could be from another source (different version, different build environment, or malicious replacement).
4. **Potential secrets / config leakage:** While no hardcoded API keys found, `release.yml` references `secrets.HOMEBREW_GITHUB_TOKEN` and `secrets.AUR_KEY`. These are proper env references, not repo leaks, but if the repo is forked or CI is misconfigured, these could be exposed in workflow logs (GitHub masks secrets by default, but `echo` or `set -x` can leak). The `.goreleaser.yml` references `{{ .Env.AUR_KEY }}` — same risk.
5. **Incorrect install URL in root `install.sh`:** References `anomalyco/opencode` (different organization). Risk of supply-chain confusion or download of wrong binary.
6. **Broken version comparison in `opencode-src/install`:** Hardcoded `installed_version="0.0.1"` makes version check useless.
7. **No artifact signing:** No `SignConfig` in `.goreleaser.yml`; no `cosign` / `gpg` / `sigstore` step in CI. Users must trust GitHub-hosted artifacts without cryptographic verification beyond HTTPS.
8. **Minimal release notes:** `release.json` body is 94 chars; no security advisory, no dependency update list, no migration guide. Project is archived, but for provenance, more metadata is needed.
9. **No vulnerability scan:** `go.mod` includes many external packages (Azure SDK, Anthropic SDK, OpenAI beta, Bubble Tea, etc.). No `govulncheck`, `trivy`, `snyk`, or `dependabot` integration visible.
10. **No SBOM:** No `syft` or `goreleaser` `sbom:` block. Dependency tree is not packaged for compliance.
11. **No signed checksums:** `checksums.txt` exists but is unsigned; if an attacker replaces artifacts and updates `checksums.txt`, users have no independent verification.
12. **Windows build missing from releases:** `opencode.exe` exists but is not in `release.json`; `.goreleaser.yml` `builds:` excludes `windows`; archive override references `windows` but no binary produced. Inconsistent.

---

## 6. What Is Missing

### CI / Pipeline
- **Vulnerability scan:** `govulncheck` (Go native), `trivy` (container/artifact), or `snyk` should run on `go.sum` and binary.
- **SBOM generation:** Add `.goreleaser.yml` `sbom:` block or run `syft` in `release.yml`; output `sbom.spdx.json` / `sbom.cyclonedx.json`.
- **Artifact signing:** Add `signs:` to `.goreleaser.yml` (GPG or Cosign / keyless Sigstore); add `cosign-sign` step in `release.yml`.
- **Checksum verification in CI:** After `goreleaser release --clean`, download artifacts and verify against `checksums.txt` and `release.json` digests in a post-release job.
- **Test gate:** Add `go test ./...` and `scripts/check_hidden_chars.sh` to `build.yml` before `goreleaser build`.
- **Module verification:** Add `go mod verify` to `build.yml`.
- **Updated actions:** Upgrade `actions/checkout@v3` → `v4`, `setup-go@v5` → `v5` (current is fine but consider `v5` with `go-version-file: go.mod`).

### Release Verification & Automation
- **Release tests:** Create `tests/test_release_artifacts.py` to fetch `release.json`, assert asset count, compare digests, verify `checksums.txt` parses correctly, check `body` length > threshold.
- **Fix `check_releases.py`:** Add pagination, correct filter (`amd64`, `arm64`, `mac`, `linux`, `windows`), compute `hashlib.sha256` on downloaded assets, compare with `digest` from API, raise exception on mismatch.
- **Fix `install.sh`:** Correct repo URL to `github.com/opencode-ai/opencode`; add `curl -sL ... | sha256sum -c checksums.txt` verification step after download; add `--verify` flag.
- **Fix `opencode-src/install`:** Replace hardcoded `installed_version="0.0.1"` with `opencode --version` parsing; add checksum download from `checksums.txt`.
- **Release notes automation:** Integrate `github-release-notes` or `git-chglog` into release workflow; generate `CHANGELOG.md` from commits.
- **Signed releases / provenance:** Use GitHub Attestations ( Sigstore / `cosign` ) for binary provenance; publish `checksums.txt.sig`.
- **Dependency audit:** Add `dependabot.yml` or `renovate.json` for `go.mod` updates; schedule weekly `govulncheck`.
- **Windows build consistency:** Either add `windows` to `.goreleaser.yml` `builds:` (and produce `opencode.exe` artifacts) or remove windows references from `install.sh` and document that Windows is unsupported.
- **Binary provenance tracking:** For `opencode.exe` in repo, record build timestamp, commit hash (`4427df58...`), Go version (`1.24.0`), and builder environment; store in `BUILD_INFO.txt` next to binary.
- **Secret rotation / audit:** Verify `HOMEBREW_GITHUB_TOKEN` and `AUR_KEY` have minimal scopes; rotate if repo was ever public with workflow logs exposed.
- **Documentation:** Add `SECURITY.md` explaining how to verify releases (download `checksums.txt`, compute `sha256sum`, compare); add `RELEASING.md` describing `scripts/release`, `.goreleaser.yml`, and CI triggers.

---

## 7. Recommendations (prioritized)

| Priority | Recommendation | Target File / Step |
|---|---|---|
| **P0 — Critical** | Fix `install.sh` repo URL (`anomalyco` → `opencode-ai`). | `install.sh` line ~180 |
| **P0 — Critical** | Verify / document origin of `opencode.exe` (build commit, Go version, source). If unverified, remove from repo or tag with provenance file. | `opencode-src/opencode.exe` + new `BUILD_INFO.txt` |
| **P0 — Critical** | Add checksum verification to both install scripts (download `checksums.txt`, compare `sha256`). | `opencode-src/install` + `install.sh` |
| **P1 — High** | Rewrite `check_releases.py`: add pagination, correct filters, digest comparison, error handling. | `check_releases.py` |
| **P1 — High** | Add `tests/test_release_artifacts.py` (assert assets, digests, body, checksums). | New file |
| **P1 — High** | Add `signs:` to `.goreleaser.yml`; add signing step to `release.yml`. | `.goreleaser.yml`, `.github/workflows/release.yml` |
| **P1 — High** | Add `govulncheck` / `trivy` scan to `build.yml` and `release.yml`. | `.github/workflows/*.yml` |
| **P2 — Medium** | Add SBOM generation (`syft` or `goreleaser` `sbom:`). | `.goreleaser.yml`, `release.yml` |
| **P2 — Medium** | Fix broken version check in `opencode-src/install` (`installed_version="0.0.1"`). | `opencode-src/install` ~line 77 |
| **P2 — Medium** | Integrate `check_hidden_chars.sh` into CI (`build.yml`, `release.yml`). | `.github/workflows/*.yml` |
| **P2 — Medium** | Upgrade `actions/checkout@v3` → `v4`; add `go mod verify`. | `.github/workflows/*.yml` |
| **P2 — Medium** | Add `windows` to `.goreleaser.yml` `builds:` OR remove windows from `install.sh`; publish `opencode.exe` artifact if supported. | `.goreleaser.yml`, `install.sh` |
| **P3 — Low** | Add `SECURITY.md` and `RELEASING.md`; improve `release.json` body via automation. | `README.md` → new docs |
| **P3 — Low** | Audit `AUR_KEY` / `HOMEBREW_GITHUB_TOKEN` scopes; consider rotating. | GitHub repo settings |

---

## Appendix — Cross-Reference Evidence
- `release.json` tag / assets / digests: verified via `python json.load` (dict, tag `v0.0.55`, 9 assets, `digest` fields present).
- `check_releases.py`: read fully (522 bytes); no pagination, no digest check.
- `opencode-src/main.go`: read fully (284 B); wrapper only.
- `opencode-src/go.mod`: first 60 lines show module / go version / direct dependencies.
- `opencode-src/README.md`: first 100 lines confirm archive status and move to Crush.
- `opencode-src/.opencode.json`: read fully; clean.
- `opencode-src/install`: first 80 + next 120 lines show correct repo URL, broken version check (`installed_version="0.0.1"`), no checksum verification.
- `opencode-src/.goreleaser.yml`: full read; `checksum`, `changelog`, `nfpms`, `brews`, `aurs`; no `signs`, no `sbom`, `builds:` excludes `windows`.
- `opencode-src/.github/workflows/build.yml` + `release.yml`: full read; env references `GITHUB_TOKEN`, `AUR_KEY`; no vulnerability / SBOM / signing steps.
- `install.sh`: first 120 + 120 lines; references `anomalyco/opencode`; no checksum verification.
- `opencode.exe`: `Get-AuthenticodeSignature` = `NotSigned`; `Get-FileHash` SHA-256 = `162B4245CCDBCAB0335178EC92FFFC7DAF6361626D89C852F1BAB25084C01F6F`; not listed in `release.json` assets.
- `.opencode/` package-lock.json: `Select-String` for secret patterns returned 0 matches.
- `internal/config/config.go`: `Select-String` found 74 matches for `api_key` / `token` / `password`; inspection of first 10 lines shows only `os.Getenv(...)` reads — no hardcoded values.
- `opencode-src/scripts/check_hidden_chars.sh`: full read; not called in CI.

---
*Audit completed. All findings are based on direct file inspection; no external network requests were made during the audit (except reference to `release.json` API values already cached locally).* 
