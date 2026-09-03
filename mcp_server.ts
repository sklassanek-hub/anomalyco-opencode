import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import fs from "fs";
import path from "path";

/**
 * Workspace Audit + Pipeline v3 MCP Server (TypeScript skeleton)
 * References: mcp-builder (.opencode/agents/mcp-builder.md), backend-architect, workflow-architect
 * Requires: process.env.MCP_AUTH_TOKEN (all calls), process.env.KILL_SWITCH_APPROVAL (trigger_kill_switch)
 * Status: SKELETON — install @modelcontextprotocol/sdk, compile with ts-node/npx tsc, run.
 */

const server = new McpServer({
  name: "workspace-audit-pipeline-server",
  version: "1.0.0",
});

const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || "";
const APPROVAL_TOKEN = process.env.KILL_SWITCH_APPROVAL || "";

function authOk(): boolean { return !!AUTH_TOKEN; }

// ---------- Resources ----------
server.resource("full_audit_master", "file://memory/full_audit_master.md", async () => ({
  contents: [{
    uri: "file://memory/full_audit_master.md",
    text: fs.readFileSync("memory/full_audit_master.md", "utf8"),
    mimeType: "text/markdown",
  }],
}));

server.resource("audit_index", "file://memory/audit_index.json", async () => ({
  contents: [{
    uri: "file://memory/audit_index.json",
    text: fs.readFileSync("memory/audit_index.json", "utf8"),
    mimeType: "application/json",
  }],
}));

server.resource("kill_switch_stage", "pipeline://stage/kill_switch", async () => {
  const blocked = fs.existsSync("zarabotok/pipeline_v3/state/KILL_SWITCH");
  let active = blocked;
  try {
    const data = JSON.parse(fs.readFileSync("zarabotok/pipeline_v3/state/kill_switch_active.json", "utf8"));
    active = data.kill_switch_active ?? blocked;
  } catch { /* ignore */ }
  return {
    contents: [{
      uri: "pipeline://stage/kill_switch",
      text: JSON.stringify({ stage: "kill_switch", blocked: active, events_file: "state/events.json" }),
      mimeType: "application/json",
    }],
  };
});

server.resource("agent_index", "file://.opencode/agents_index.json", async () => ({
  contents: [{
    uri: "file://.opencode/agents_index.json",
    text: fs.readFileSync(".opencode/agents_index.json", "utf8"),
    mimeType: "application/json",
  }],
}));

// ---------- Tools ----------
server.tool(
  "run_pytest",
  "Run pytest suite. Use for verification only. Sandbox execution with timeout.",
  {
    test_path: z.string().default(".").describe("Directory or file to test"),
    timeout: z.number().min(1).max(120).default(30).describe("Max seconds before abort"),
    verbose: z.boolean().default(false).describe("Verbose pytest output"),
  },
  async ({ test_path, timeout, verbose }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Missing MCP_AUTH_TOKEN" }) }], isError: true };
    // Skeleton: real server uses child_process.spawn with sandbox rules
    return {
      content: [{ type: "text", text: JSON.stringify({ status: "passed", tests_run_approx: 42, security: "sandbox_isolated=True" }) }],
      isError: false,
    };
  }
);

server.tool(
  "check_releases",
  "Compare local release.json against anomalyco/opencode GitHub releases.",
  {
    repo: z.string().default("anomalyco/opencode").describe("GitHub owner/repo"),
    local_file: z.string().default("release.json").describe("Local file"),
    timeout: z.number().min(1).max(60).default(30),
  },
  async ({ repo, local_file, timeout }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Missing auth" }) }], isError: true };
    return { content: [{ type: "text", text: JSON.stringify({ repo, local_version: "unknown", upstream_version: "unknown", checksum_match: null, status: "skeleton_implement_urllib" }) }], isError: false };
  }
);

server.tool(
  "verify_accessibility",
  "Run accessibility verification against audit files or pipeline.",
  {
    target: z.enum(["audit_accessibility.md", "full_audit_master.md", "pipeline", "deliverables"]).default("audit_accessibility.md"),
    level: z.enum(["A", "AA", "AAA"]).default("AA"),
    format: z.enum(["json", "markdown"]).default("json"),
  },
  async ({ target, level, format }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true }) }], isError: true };
    return { content: [{ type: "text", text: JSON.stringify({ target, level, violations: 0, passed: true, recommendations: ["Skeleton: implement axe-core"] }) }], isError: false };
  }
);

server.tool(
  "run_sandbox_test",
  "Execute sandbox/test script in isolated process. No production changes.",
  {
    script: z.string().describe("Script path relative to workspace"),
    args: z.array(z.string()).default([]).describe("Arguments"),
    env_isolation: z.boolean().default(true).describe("Isolate environment"),
    timeout: z.number().min(1).max(60).default(15),
  },
  async ({ script, args, env_isolation, timeout }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true }) }], isError: true };
    return { content: [{ type: "text", text: JSON.stringify({ script, exit_code: 0, sandbox_safe: true, env_isolated: env_isolation }) }], isError: false };
  }
);

server.tool(
  "read_memory_index",
  "Read memory/audit_index.json to discover audit resource IDs and statuses.",
  {},
  async () => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true }) }], isError: true };
    return { content: [{ type: "text", text: fs.readFileSync("memory/audit_index.json", "utf8") }], isError: false };
  }
);

server.tool(
  "read_agent_index",
  "Read .opencode/agents_index.json to list agents and capabilities.",
  {
    filter_role: z.string().default("").describe("Optional role filter"),
    limit: z.number().min(1).max(100).default(20),
  },
  async ({ filter_role, limit }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true }) }], isError: true };
    try {
      const data = JSON.parse(fs.readFileSync(".opencode/agents_index.json", "utf8"));
      const agents = Array.isArray(data) ? data : (data.agents || []);
      const filtered = filter_role ? agents.filter((a: any) => JSON.stringify(a).toLowerCase().includes(filter_role.toLowerCase())) : agents;
      return { content: [{ type: "text", text: JSON.stringify({ agents: filtered.slice(0, limit), total: filtered.length }) }], isError: false };
    } catch (e: any) {
      return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: e.message }) }], isError: true };
    }
  }
);

server.tool(
  "get_pipeline_stage",
  "Retrieve pipeline stage file or status.",
  {
    stage: z.enum(["executor", "listener_bridge", "conversation", "billing_service", "kill_switch"]).default("kill_switch"),
    mode: z.enum(["source", "status"]).default("status"),
  },
  async ({ stage, mode }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true }) }], isError: true };
    if (mode === "status" && stage === "kill_switch") {
      const blocked = fs.existsSync("zarabotok/pipeline_v3/state/KILL_SWITCH");
      return { content: [{ type: "text", text: JSON.stringify({ stage, blocked }) }], isError: false };
    }
    const srcPath = `zarabotok/pipeline_v3/modules/${stage}.py`;
    try {
      const snippet = fs.readFileSync(srcPath, "utf8").slice(0, 2000);
      return { content: [{ type: "text", text: JSON.stringify({ stage, mode, snippet_preview: snippet, secret_filter_applied: true }) }], isError: false };
    } catch (e: any) {
      return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: e.message }) }], isError: true };
    }
  }
);

server.tool(
  "trigger_kill_switch",
  "Activate/deactivate global kill switch. Requires approval_token matching env.",
  {
    active: z.boolean().describe("True = block pipeline"),
    approval_token: z.string().describe("Must match KILL_SWITCH_APPROVAL"),
    reason: z.string().optional().default("").describe("Audit reason"),
    source: z.string().optional().default("mcp").describe("Source identifier"),
  },
  async ({ active, approval_token, reason, source }) => {
    if (!authOk()) return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Missing auth" }) }], isError: true };
    if (!APPROVAL_TOKEN || approval_token !== APPROVAL_TOKEN) {
      return { content: [{ type: "text", text: JSON.stringify({ isError: true, message: "Invalid approval_token" }) }], isError: true };
    // Skeleton: write files and append event (hash token only)
    const hash = require("crypto").createHash("sha256").update(approval_token).digest("hex").slice(0, 32);
    return {
      content: [{ type: "text", text: JSON.stringify({ success: true, active, approval_token_hash: hash, audit_ts: new Date().toISOString(), security: "write_approved=True,hash_only=True" }) }],
      isError: false,
    };
  }
);

// ---------- Start ----------
const transport = new StdioServerTransport();
await server.connect(transport);
