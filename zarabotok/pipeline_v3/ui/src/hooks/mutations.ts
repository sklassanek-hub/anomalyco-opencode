// Мутации (WRITE-эндпоинты). Все — с оптимистичным инвалидированием кэша.
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { post, patch } from '../lib/api';
import type { DealPatch, DecisionRequest } from '../lib/types';

function invalidateAll(client: ReturnType<typeof useQueryClient>, keys: string[][]) {
  keys.forEach((k) => client.invalidateQueries({ queryKey: k }));
}

export function useFilterDecision() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: DecisionRequest) => post<unknown>('/api/filter/decision', body),
    onSuccess: () => invalidateAll(client, [['filter-pending'], ['orders'], ['deals']]),
  });
}

export function usePatchDeal() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch: body }: { id: string; patch: DealPatch }) =>
      patch<unknown>(`/api/deals/${encodeURIComponent(id)}`, body),
    onSuccess: () => invalidateAll(client, [['deals'], ['deal'], ['orders'], ['invoices']]),
  });
}

export function useResendInvoice() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => post<unknown>(`/api/invoices/${encodeURIComponent(id)}/resend`),
    onSuccess: () => invalidateAll(client, [['invoices'], ['deals']]),
  });
}

export function useMarkInvoicePaid() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => post<unknown>(`/api/invoices/${encodeURIComponent(id)}/mark-paid`),
    onSuccess: () => invalidateAll(client, [['invoices'], ['payments'], ['deals'], ['orders']]),
  });
}

export function useCancelTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => post<unknown>(`/api/tasks/${encodeURIComponent(id)}/cancel`),
    onSuccess: () => invalidateAll(client, [['tasks'], ['task']]),
  });
}

export function useReassignTask() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, agent }: { id: string; agent: string }) =>
      post<unknown>(`/api/tasks/${encodeURIComponent(id)}/reassign`, { agent }),
    onSuccess: () => invalidateAll(client, [['tasks'], ['task'], ['agents']]),
  });
}