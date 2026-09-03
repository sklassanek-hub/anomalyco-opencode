// React Query хуки для всех эндпоинтов API. Polling: 30с списки, 10с health/metrics.
import { useQuery } from '@tanstack/react-query';
import { get, ApiError } from '../lib/api';
import type {
  AgentsResponse,
  DealsResponse,
  EventsResponse,
  FunnelResponse,
  HealthResponse,
  InvoicesResponse,
  LogsResponse,
  MetricsResponse,
  OrderDetail,
  OrdersResponse,
  PaymentsResponse,
  PendingResponse,
  RepliesResponse,
  SettingsResponse,
  Task,
  TasksResponse,
} from '../lib/types';

const EMPTY_ORDERS: OrdersResponse = { rows: [], count: 0, columns: [] };
const EMPTY_DEALS: DealsResponse = { items: [], count: 0 };
const EMPTY_REPLIES: RepliesResponse = { items: [], count: 0 };
const EMPTY_PENDING: PendingResponse = { items: [], count: 0 };
const EMPTY_AGENTS: AgentsResponse = { items: [], count: 0 };
const EMPTY_TASKS: TasksResponse = { items: [], count: 0 };
const EMPTY_INVOICES: InvoicesResponse = { items: [], count: 0 };
const EMPTY_PAYMENTS: PaymentsResponse = { items: [], count: 0 };
const EMPTY_EVENTS: EventsResponse = { events: [], total: 0, limit: 0 };
const EMPTY_LOGS: LogsResponse = { logs: [], items: [], count: 0 };
const EMPTY_FUNNEL: FunnelResponse = {
  counts: {}, total: 0, order: [], conversions: [],
  won_to_paid: { from: 'won', to: 'paid', count_from: 0, count_to: 0, percent: 0 },
  ru: {},
};

export function is404(e: unknown): boolean {
  return e instanceof ApiError && e.status === 404;
}

export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      try {
        return await get<OrdersResponse>('/api/orders');
      } catch (e) {
        if (is404(e)) return EMPTY_ORDERS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useOrder(id: string | undefined) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: async () => {
      try {
        return await get<OrderDetail>(`/api/orders/${encodeURIComponent(id || '')}`);
      } catch (e) {
        if (is404(e)) return null;
        throw e;
      }
    },
    enabled: !!id,
  });
}

export function useDeals() {
  return useQuery({
    queryKey: ['deals'],
    queryFn: async () => {
      try {
        return await get<DealsResponse>('/api/deals');
      } catch (e) {
        if (is404(e)) return EMPTY_DEALS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useDeal(id: string | undefined) {
  return useQuery({
    queryKey: ['deal', id],
    queryFn: async () => {
      try {
        return await get<DealsResponse>(`/api/deals/${encodeURIComponent(id || '')}`);
      } catch (e) {
        if (is404(e)) return null;
        throw e;
      }
    },
    enabled: !!id,
  });
}

export function useReplies() {
  return useQuery({
    queryKey: ['replies'],
    queryFn: async () => {
      try {
        return await get<RepliesResponse>('/api/replies');
      } catch (e) {
        if (is404(e)) return EMPTY_REPLIES;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useReply(id: string | undefined) {
  return useQuery({
    queryKey: ['reply', id],
    queryFn: async () => {
      try {
        return await get<RepliesResponse>(`/api/replies/${encodeURIComponent(id || '')}`);
      } catch (e) {
        if (is404(e)) return null;
        throw e;
      }
    },
    enabled: !!id,
  });
}

export function usePendingFilter() {
  return useQuery({
    queryKey: ['filter-pending'],
    queryFn: async () => {
      try {
        return await get<PendingResponse>('/api/filter/pending');
      } catch (e) {
        if (is404(e)) return EMPTY_PENDING;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      try {
        return await get<AgentsResponse>('/api/agents');
      } catch (e) {
        if (is404(e)) return EMPTY_AGENTS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useTasks() {
  return useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      try {
        return await get<TasksResponse>('/api/tasks');
      } catch (e) {
        if (is404(e)) return EMPTY_TASKS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: async () => {
      try {
        return await get<Task>(`/api/tasks/${encodeURIComponent(id || '')}`);
      } catch (e) {
        if (is404(e)) return null;
        throw e;
      }
    },
    enabled: !!id,
  });
}

export function useMetrics() {
  return useQuery({
    queryKey: ['metrics'],
    queryFn: async () => {
      try {
        return await get<MetricsResponse>('/api/metrics');
      } catch (e) {
        if (is404(e)) return {};
        throw e;
      }
    },
    refetchInterval: 10000,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      try {
        return await get<HealthResponse>('/api/health');
      } catch (e) {
        if (is404(e)) return {};
        throw e;
      }
    },
    refetchInterval: 10000,
  });
}

export function useLogs(params?: { service?: string; level?: string; limit?: number; since?: string }) {
  const q = new URLSearchParams();
  if (params?.service) q.set('service', params.service);
  if (params?.level) q.set('level', params.level);
  if (params?.limit) q.set('limit', String(params.limit));
  if (params?.since) q.set('since', params.since);
  const qs = q.toString();
  return useQuery({
    queryKey: ['logs', qs],
    queryFn: async () => {
      try {
        return await get<LogsResponse>(`/api/logs?${qs}`);
      } catch (e) {
        if (is404(e)) return EMPTY_LOGS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useEvents(limit = 50) {
  return useQuery({
    queryKey: ['events', limit],
    queryFn: async () => {
      try {
        return await get<EventsResponse>(`/api/events?limit=${limit}`);
      } catch (e) {
        if (is404(e)) return EMPTY_EVENTS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useInvoices() {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      try {
        return await get<InvoicesResponse>('/api/invoices');
      } catch (e) {
        if (is404(e)) return EMPTY_INVOICES;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function usePayments() {
  return useQuery({
    queryKey: ['payments'],
    queryFn: async () => {
      try {
        return await get<PaymentsResponse>('/api/payments');
      } catch (e) {
        if (is404(e)) return EMPTY_PAYMENTS;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useFunnel() {
  return useQuery({
    queryKey: ['funnel'],
    queryFn: async () => {
      try {
        return await get<FunnelResponse>('/api/funnel');
      } catch (e) {
        if (is404(e)) return EMPTY_FUNNEL;
        throw e;
      }
    },
    refetchInterval: 30000,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      try {
        return await get<SettingsResponse>('/api/settings');
      } catch (e) {
        if (is404(e)) return {};
        throw e;
      }
    },
    refetchInterval: 60000,
  });
}