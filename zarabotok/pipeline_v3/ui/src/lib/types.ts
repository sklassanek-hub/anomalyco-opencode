// Типы данных API zarabotok/pipeline_v3.
// API расширяется параллельно — поля опциональны и допускают null.

export type Tone = 'ok' | 'warn' | 'err' | 'info' | 'none' | 'gray';

export interface ApiErrorBody {
  error?: string;
  path?: string;
}

// ---------- orders ----------

export interface InvoiceBrief {
  no?: string;
  amount?: string;
  status?: string;
  paid_at?: string;
  payment_link?: string;
}

export interface ExecTaskBrief {
  status?: string;
  created_at?: string;
  done_at?: string;
  agents?: string[];
}

export interface PaymentBrief {
  status?: string;
  amount?: string;
  paid_at?: string;
  method?: string;
}

export interface OrderRow {
  url: string;
  status?: string;
  raw_status?: string;
  title?: string | null;
  budget?: string | null;
  score?: number | null;
  source?: string | null;
  channel?: string | null;
  contact?: string | null;
  ts?: string | null;
  notes?: string | null;
  messages?: number;
  invoice?: InvoiceBrief | null;
  exec_task?: ExecTaskBrief | null;
  payment?: PaymentBrief | null;
}

export interface OrdersResponse {
  rows: OrderRow[];
  count: number;
  columns: string[];
}

export interface Message {
  id?: string;
  direction?: string; // in/out, incoming/outgoing
  channel?: string;
  text?: string;
  ts?: string;
  from?: string;
}

export interface AgentsActivity {
  agent?: string;
  file?: string;
  action?: string;
  text?: string;
  ts?: string;
  artifacts?: { name?: string; size?: number }[];
}

export interface OrderDetail extends Omit<OrderRow, 'messages'> {
  description?: string | null;
  messages?: Message[] | number;
  agents_activity?: AgentsActivity[];
  task?: ExecTaskBrief | null;
  raw?: unknown;
}

// ---------- funnel ----------

export interface Conversion {
  from: string;
  to: string;
  count_from: number;
  count_to: number;
  percent: number;
}

export interface FunnelResponse {
  counts: Record<string, number>;
  total: number;
  order: string[];
  conversions: Conversion[];
  won_to_paid: Conversion;
  ru: Record<string, string>;
}

// ---------- deals ----------

export interface Deal {
  id: string;
  url?: string;
  title?: string | null;
  client?: string | null;
  contact?: string | null;
  budget?: string | null;
  source?: string | null;
  score?: number | null;
  automation_score?: number | null;
  agent?: string | null;
  assigned_agent?: string | null;
  stage?: string;
  status?: string;
  raw_status?: string;
  invoice_status?: string | null;
  note?: string | null;
  ts?: string | null;
  messages?: Message[];
  invoice?: InvoiceItem | null;
  exec_task?: ExecTaskBrief | null;
  agents_activity?: AgentsActivity[];
}

export interface DealsResponse {
  items: Deal[];
  count: number;
}

// ---------- replies ----------

export interface Reply {
  id: string;
  order?: string;
  order_url?: string;
  title?: string;
  model?: string;
  variant?: string;
  status?: string;
  response_rate?: number;
  prompt?: string;
  response?: string;
  ts?: string;
  tokens?: number;
  latency_ms?: number;
}

export interface RepliesResponse {
  items: Reply[];
  count: number;
}

// ---------- filter pending ----------

export interface PendingFilter {
  order?: string;
  url?: string;
  title?: string;
  score?: number;
  reason_codes?: string[];
  suggested_action?: string;
}

export interface PendingResponse {
  items: PendingFilter[];
  count: number;
}

// ---------- agents ----------

export interface Agent {
  id: string;
  file?: string;
  name?: string;
  type?: string;
  status?: string;
  load?: number;
  active_tasks?: number;
  avg_time?: number;
  success_rate?: number;
}

export interface AgentsResponse {
  items: Agent[];
  count: number;
}

// ---------- tasks ----------

export interface TaskArtifact {
  name?: string;
  size?: number;
}

export interface Task {
  id: string;
  url?: string;
  deal?: string;
  deal_url?: string;
  title?: string;
  type?: string;
  agent?: string;
  assigned_agent?: string;
  status?: string;
  deadline?: string | null;
  created_at?: string;
  started_at?: string;
  done_at?: string;
  note?: string;
  artifacts?: TaskArtifact[];
  quality?: Record<string, string>;
}

export interface TasksResponse {
  items: Task[];
  count: number;
}

// ---------- metrics ----------

export interface MetricWorker {
  name: string;
  status?: string;
  pid?: number;
  uptime?: number;
  error_rate?: number;
  last_seen?: string;
}

export interface MetricsResponse {
  throughput_per_stage?: Record<string, number>;
  latency?: Record<string, number | string>;
  latency_per_stage?: Record<string, { p50?: number; p95?: number }>;
  workers?: MetricWorker[];
  errors?: Record<string, number>;
  kpi?: Record<string, number | string>;
  health?: string;
  active_agents?: number;
  pending_tasks?: number;
}

// ---------- logs / events ----------

export interface LogEntry {
  ts?: string;
  service?: string;
  level?: string;
  text?: string;
  msg?: string;
  trace_id?: string;
  links?: string[];
}

export interface LogsResponse {
  logs?: LogEntry[];
  items?: LogEntry[];
  count?: number;
  total?: number;
}

export interface EventItem {
  ts?: string;
  source?: string;
  text?: string;
  level?: string;
}

export interface EventsResponse {
  events: EventItem[];
  total: number;
  limit: number;
}

// ---------- invoices / payments ----------

export interface InvoiceItem {
  id?: string;
  no?: string;
  url?: string;
  deal?: string;
  title?: string;
  amount?: string;
  method?: string;
  status?: string;
  paid_at?: string;
  created_at?: string;
  sent_at?: string;
  payment_link?: string;
  requisites?: string;
  note?: string;
}

export interface InvoicesResponse {
  items: InvoiceItem[];
  count: number;
}

export interface PaymentItem {
  url?: string;
  deal?: string;
  status?: string;
  pay_status?: string;
  amount?: string;
  method?: string;
  paid_at?: string;
  ts?: string;
  type?: string;
}

export interface PaymentsResponse {
  items: PaymentItem[];
  count: number;
  derived?: boolean;
}

// ---------- settings / health ----------

export interface SettingsResponse {
  config?: {
    executors?: Record<string, { model?: string; status?: string; url?: string; temperature?: number; max_tokens?: number }>;
    payment?: {
      methods?: Record<string, { enabled?: boolean; note?: string; number?: string; holder?: string; phone?: string; address?: string; networks?: Record<string, string> }>;
      wallet?: string;
      currency?: string;
    };
    ui?: { panel_port?: number; api_port?: number };
    sender?: Record<string, unknown>;
    [k: string]: unknown;
  };
  storage?: unknown;
  panel_port?: number;
  readonly?: boolean;
}

export interface HealthResponse {
  status?: string;
  ok?: boolean;
  workers?: Record<string, string | boolean>;
  services?: Record<string, string | boolean>;
  model?: string;
  models?: string[];
}

// ---------- mutations ----------

export type Decision = 'accept' | 'reject' | 'edit';

export interface DecisionRequest {
  order: string;
  decision: Decision;
  note?: string;
}

export type DealPatch = Record<string, unknown>;