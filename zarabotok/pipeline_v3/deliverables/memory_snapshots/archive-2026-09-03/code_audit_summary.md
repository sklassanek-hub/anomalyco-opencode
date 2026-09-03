# CodeSecurityAudit — opencode-src (Activated: 2026-08-31)
Agent: CodeSecurityAuditor | Source: C:\Users\klass\OneDrive\Desktop\work\opencode-src | Report: memory/code_audit_summary.md

---

## 1. Executive / Scope
Inspected `opencode-src/` (modular Go CLI), root test artifacts (`test_openai.go`, `test_request.json`, `test_stream.json`), `.opencode.json`, `opencode-schema.json` (draft-07), `.github/workflows/`, binary `opencode.exe`, and brief `internal/` package surveys (`app`, `permission`, `config`, `llm/provider`). No container/CI security scans present.

---

## 2. Architecture (Modular, CLI-Centric, Schema-Validated)

### Structure — Modular (not monolithic)
- `main.go` (284 src bytes): single entry, delegates to `cmd.Execute()`; panic recovery via `logging.RecoverPanic` (`main.go:10-13`).
- `cmd/root.go` (~300 lines): Cobra CLI (`Use: "opencode"`), interactive TUI (`tea.NewProgram`), non-interactive `-p`, format validation (`format.IsValid`), LSP init (`initMCPTools`), DB connect (`db.Connect`), config load (`config.Load`).
- `cmd/schema/`: schema subcommand folder.
- `internal/` packages (16 dirs): `app`, `completions`, `config`, `db`, `diff`, `fileutil`, `format`, `history`, `llm` (agent/provider/tools/prompt/models), `logging`, `lsp`, `message`, `permission`, `pubsub`, `session`, `tui`, `version`. Highly decomposed.

### APIs / Interfaces
- **No exposed HTTP/REST server** (terminal-only AI assistant). LLM communication is outbound via `internal/llm/provider/` (OpenAI, Anthropic, Gemini, Copilot, Azure, Bedrock, VertexAI).
- **Schema-defined**: `opencode-schema.json` (draft-07, 12659 bytes) defines `agent` properties (`model` enum #51-61, `maxTokens` min 1, `reasoningEffort` enum `low/medium/high`, `temperature`, etc.). `.opencode.json` references `"$schema": "./opencode-schema.json"`.
- **Config**: `internal/config/config.go` loads env (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc., lines 258-280; `AZURE_OPENAI_API_KEY` line 278; `AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY` line 392; `LoadGitHubToken()` line 430). Uses Viper + `os.Getenv`.

### Validation
- `config.Validate()` (`config.go:609`) validates agent models, max tokens (>0), reasoning effort, provider IDs.
- `format.IsValid()` validates output format flags (`root.go` area).
- `permission.Request()` validates session-level grants (`permission.go:69-103`) via `filepath.Dir` + session ID match; no explicit path-traversal rejection visible (relies on `filepath.Dir` normalization only).

---

## 3. Security Analysis

### 3.1 Input Validation — Partial
- CLI args validated (format, cwd chdir, debug bool).
- Agent model enum restricts model IDs (schema + `validateAgent`).
- **Weakness**: No visible sanitization of `prompt` string or file paths passed to LLM/tool execution before execution. Tool parameter `Params any` (`permission.go:27`) is untyped; could carry arbitrary JSON payload into tool execution.

### 3.2 Authentication / Authorization — Missing
- **No auth middleware** in `cmd/root.go`; CLI runs with user privileges only.
- **No role-based access control** (RBAC): `internal/permission/permission.go` implements session-level `Grant/Deny/Request` with `autoApproveSessions` list (`permission.go:105`), but roles/users are absent. Schema (`opencode-schema.json`) contains zero auth/role fields (only `agent`, `lsp`).
- **No API-key verification** for local CLI operation; keys only used for external LLM endpoints.

### 3.3 Secret Handling — Env-Based, No Hardcoding
- `internal/config/config.go` reads secrets exclusively from environment (lines 258-280, 392). No literal API keys in `main.go`, `cmd/`, or `internal/` source inspected.
- **Caution**: `test_openai.go` (root) hardcodes `option.WithAPIKey("lm-studio")` and points to `http://127.0.0.1:1234/v1`. This is test-only, not production, but demonstrates a pattern of hardcoded test credentials near source.
- `opencode.exe` binary (61.6 MB, dated 29.08.2026) is present in source tree; no evidence of embedded secrets without binary analysis, but binary exposure increases risk if distributed unverified.

### 3.4 Sandbox / Isolation — None
- Agent/tool execution occurs in-process (`app.RunNonInteractive` → `CoderAgent.Run` → tool invocation via `pubsub` broker). No container (`docker`/`podman`), `chroot`, `seccomp`, or subprocess isolation observed in `internal/app/app.go`, `internal/llm/`, or `cmd/root.go`.
- `permission.Request()` uses `pubsub.Broker`; grants are synchronous (`respCh <- bool`) with no timeout guard on grant side (only on request via `<-respCh` — actually blocks until granted/denied; no explicit timeout in shown code, risk of deadlock or indefinite hang if subscriber misses event).

### 3.5 Kill-Switch / Panic Recovery — Partial
- `main.go`: `defer logging.RecoverPanic("main", ...)` and `ErrorPersist`.
- `cmd/root.go`: `defer logging.RecoverPanic("TUI-message-handler", ...)` (line 136), `RecoverPanic("MCP-goroutine", ...)` (line 197), `RecoverPanic(fmt.Sprintf("subscription-%s", name), nil)` (line 219).
- **No explicit agent kill-switch** (e.g., `SIGTERM` handler to abort LLM call, max execution time per tool, or `context.WithTimeout` enforced at agent level). `ctx, cancel := context.WithCancel(context.Background())` exists (`root.go`), but cancellation relies on user interrupt or shutdown.

### 3.6 Rate Limiting — Absent
- No token-bucket, request throttling, or per-session LLM-rate guard found in `internal/`, `cmd/`, or `app`. Direct outbound LLM calls via `provider/openai.go`, `anthropic.go`, etc., unthrottled.

---

## 4. Strong Points (Confirmed)
1. **Go structured / typed**: Strong typing, interfaces (`permission.Service`, `pubsub.Broker`), explicit error returns.
2. **Schema validation**: `opencode-schema.json` (draft-07) defines agent configs, model enums, token limits; `.opencode.json` references it.
3. **CLI interface**: Cobra with flags (`-p`, `-f`, `-c`, `-d`, `-q`), interactive TUI (`bubbletea`), non-interactive JSON output.
4. **Modular decomposition**: 16 `internal/` packages; `llm/provider/` abstracts vendors.
5. **Permission framework**: Session-level grant/deny/auto-approve (`permission.go`); not just open-loop.
6. **Panic resilience**: Multiple `RecoverPanic` deferrals in CLI/TUI/MCP paths.
7. **Environment-based secrets**: No hardcoded production keys in source inspected.

---

## 5. Weak Points (Confirmed)
1. **No auth middleware**: CLI execution is unauthenticated; any local user can run with configured env keys.
2. **Unverified external LLM endpoint**: `internal/llm/provider/openai.go` allows arbitrary `baseURL` (`WithOpenAIBaseURL`, line 416-418); no TLS verification override check, no endpoint allow-list, no cert pinning visible.
3. **No rate limiting / quota**: LLM and tool calls unlimited; risk of cost exhaustion or abuse.
4. **Test files minimal / non-comprehensive**: Only three root artifacts:
   - `test_openai.go`: connects to local `127.0.0.1:1234` with hardcoded `lm-studio` key; tests streaming/non-streaming; no assertions, just print.
   - `test_request.json`: `{"model":"mistralai/...","messages":[{"role":"user","content":"test"}],"max_tokens":100}` — static fixture.
   - `test_stream.json`: same + `"stream":true` — static fixture.
   No `tests/` directory under `opencode-src/`; no `*_test.go` files found inside source tree.
5. **No container isolation for agent execution**: Tools / code runners execute in same process/user context.
6. **Binary exposure**: `opencode.exe` (61.6 MB) present in repo; unverified build, no signature/checksum file, no `checksums.txt` or `sigstore` reference in `.goreleaser.yml`.
7. **CI only builds**: `.github/workflows/build.yml` (snapshot build with `goreleaser`); `.github/workflows/release.yml` (release with `GITHUB_TOKEN`/`AUR_KEY`). No `go test`, `trivy`, `snyk`, `codeql`, `bandit`/`semgrep`, dependency-check, or SBOM generation in CI.
8. **No structured audit logging**: `internal/logging/logger.go` provides info/warn/error; no audit event schema for permission grants, LLM calls, tool execution, or file modifications.

---

## 6. Gaps / Missing (Explicitly Searched)
| Area | Status | Evidence / File Refs |
|---|---|---|
| Unit tests (`*_test.go` inside `opencode-src/`) | **Missing** | None found; only root `test_openai.go` |
| Integration / E2E tests | **Missing** | No `tests/` folder; no CI `go test` step |
| Vulnerability scanning (deps / container / binary) | **Missing** | No `trivy`, `snyk`, `semgrep`, `bandit`, `osv-scanner` in `.github/workflows/`; `go.sum` present but not audited |
| SBOM generation | **Missing** | `.goreleaser.yml` (1.9 KB) has no `sbom` section |
| Audit logging (security events) | **Missing** | `logging/` has general logs; no audit event type for permission/tool/LLM |
| Role-Based Permissions (RBAC) | **Missing** | Schema and `permission.go` have no role/user fields |
| Rate limiting / quota enforcement | **Missing** | No middleware; provider files unthrottled |
| Authentication middleware | **Missing** | `cmd/root.go`: no auth check |
| Sandbox / container isolation | **Missing** | `internal/app/app.go`: in-process execution |
| Binary signing / verification | **Missing** | `opencode.exe` unsigned; `.goreleaser.yml` no `signs`/`cosign` |
| Input sanitization for tool params | **Partial / weak** | `permission.go`: `Params any` untyped; `filepath.Dir` used but no traversal guard explicit |
| Kill-switch / execution timeout per agent call | **Missing** | `context.WithCancel` exists but no `WithTimeout` enforced at agent level |

---

## 7. Detailed File References

### Source / Config / Schema
- `opencode-src/main.go` — entry, panic recovery
- `opencode-src/cmd/root.go` — CLI (Cobra), TUI, non-interactive, config load, DB connect, MCP init
- `opencode-src/cmd/schema/` — schema subcommand
- `opencode-src/.opencode.json` — references `opencode-schema.json`; LSP config (`gopls`)
- `opencode-src/opencode-schema.json` — draft-07 schema; agent definitions, model enums, token limits; 12659 bytes; no auth/role fields
- `opencode-src/internal/config/config.go` — env secret loading (`ANTHROPIC_API_KEY` etc., lines 258-280, 392, 430); validation (`Validate`, line 609); agent config (`AgentName`)
- `opencode-src/internal/permission/permission.go` — session-level grant/deny/automate; `CreatePermissionRequest`; `pubsub.Broker`; sync `pendingRequests`; `filepath.Dir`
- `opencode-src/internal/app/app.go` — app creation, non-interactive run (`RunNonInteractive`), agent execution; no sandbox
- `opencode-src/internal/llm/provider/openai.go` — `baseURL` configurable (`WithOpenAIBaseURL`, line 416); `openaiClientOptions` with `option.WithBaseURL`
- `opencode-src/internal/logging/logger.go`, `message.go`, `writer.go` — log infrastructure

### Tests (Root — Not Under Source Tree)
- `test_openai.go` (1148 bytes) — hardcoded local endpoint `127.0.0.1:1234/v1`, key `"lm-studio"`; streaming test; no assertions
- `test_request.json` (109 bytes) — static request fixture
- `test_stream.json` (128 bytes) — static stream fixture

### CI / Build / Release
- `opencode-src/.github/workflows/build.yml` (718 bytes) — `build --snapshot --clean`; no tests / security scans
- `opencode-src/.github/workflows/release.yml` (830 bytes) — `release --clean`; uses `secrets.HOMEBREW_GITHUB_TOKEN`, `secrets.AUR_KEY`
- `opencode-src/.goreleaser.yml` (1866 bytes) — build/release config; no SBOM / sign / verify settings
- `opencode-src/scripts/` — `check_hidden_chars.sh`, `release`, `snapshot`; no security scripts

### Binary / Artifacts
- `opencode-src/opencode.exe` (61,628,416 bytes, 29.08.2026) — binary present in repo; unverified; potential exposure

---

## 8. Recommendations (Prioritized)

### Immediate (P0)
1. **Add auth / access control**: Even CLI-level config auth (e.g., require `OPENCODE_API_KEY` or local token for sensitive operations) or enforce OS-user permission checks before agent execution. Add middleware layer in `cmd/root.go` or `internal/app/app.go`.
2. **Rate limits**: Implement token/request throttling in `internal/llm/provider/` or at `app` layer (e.g., max 10 LLM calls/min per session, max tokens per request enforced at provider wrapper).
3. **Audit events**: Extend `internal/logging/` or add `internal/audit/` with structured events: `PermissionGrant`, `LLMCall` (model, latency, token count), `ToolExecution` (tool name, params sanitized, result status), `FileModification`. Log to structured format (JSON) with session ID and timestamp.
4. **Kill-switch / timeouts**: Enforce `context.WithTimeout` per agent action and LLM call; expose `SIGTERM` / `SIGINT` handler that sets `cancel()` and aborts streaming.

### Short-Term (P1)
5. **Sandboxes / isolation**: Run agent tool execution in sandboxed subprocess (e.g., `nsjail`, `firejail`, container with restricted FS/network) or at minimum restricted `os/exec` with `Seccomp` profile. Do not allow direct `exec` of arbitrary commands in-process.
6. **Input sanitization**: For `permission.Request()` and tool execution, validate `Path` against path-traversal (`..`), sanitize `Params` (reject unknown keys, enforce schema per tool), and validate `ToolName` against allow-list.
7. **Endpoint verification**: In `provider/openai.go` and others, enforce an allow-list of base URLs or require TLS with valid cert; disable custom base URL unless explicitly allowed via config flag `allowCustomEndpoint`.
8. **Expand testing**: Create `opencode-src/internal/*_test.go` files; add integration tests for `permission`, `config.Validate`, `provider` mock responses; replace root `test_openai.go` with proper `test/` suite with assertions.

### Medium-Term (P2)
9. **CI security pipeline**: Add to `.github/workflows/build.yml`: `go test ./...`, `go mod verify`, dependency vulnerability scan (`gosum` check + `osv-scanner` or `trivy fs`), static analysis (`gosec`, `staticcheck`), secrets scan (`trufflehog` or `git-secret` for accidental commits).
10. **SBOM and binary signing**: Add `sbom:` section to `.goreleaser.yml`; sign `opencode.exe` with `cosign` / `sigstore`; publish `checksums.txt` and `.sig` files; verify binary in release workflow.
11. **Role-based permissions (RBAC)**: Extend schema (`opencode-schema.json`) with `user`, `role`, `permissions` fields; implement `RoleService` in `internal/permission/`; enforce role checks before `Grant`.
12. **Container isolation for CI / build**: Build in container with `Dockerfile` to prevent host pollution; use `goreleaser` with `snapcraft`/`homebrew` only after verification.

---

## 9. Verification Notes
- All source inspections performed with `Get-Content` / `Select-String` on Windows PowerShell (`C:\Users\klass\OneDrive\Desktop\work`).
- No `grep`/`head`/`cat` available; used `Select-String`, `Select-Object -Skip/First`.
- No binary reverse-engineering performed on `opencode.exe`; assessment based on presence, size, and absence of signing/checksum artifacts.
- No network access to external endpoints; `test_openai.go` points to localhost (unreachable) with dummy key.
- Audit outputs: `memory/accessibility_audit_summary.md`, `memory/release_audit_summary.md`, `memory/workflow_audit_summary.md`, `memory/code_audit_summary.md` (this file).

---
*End of audit. Recommendations should be tracked in `MEMORY.md` or agent task list and verified by re-running CI + security scans after implementation.*
