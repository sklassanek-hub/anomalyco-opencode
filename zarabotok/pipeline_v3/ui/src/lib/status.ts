// Статусы, стадии воронки, канбан-колонки и маппинги по ТЗ.
import type { Tone } from './types';

export const STAGE_RU: Record<string, string> = {
  new: 'Новые',
  draft: 'Черновики',
  sent: 'Отправлено',
  reply: 'Ответили',
  negotiation: 'Переговоры',
  won: 'Выиграно',
  invoice: 'Счёт',
  paid: 'Оплачено',
  closed: 'Закрыто',
  lost: 'Закрыто',
  archive: 'Закрыто',
};

export const KANBAN_COLUMNS = ['New', 'Replied', 'Conversation', 'Won', 'Invoice', 'Paid', 'Closed'];

export const KANBAN_TO_RAW: Record<string, string> = {
  New: 'new',
  Replied: 'reply',
  Conversation: 'negotiation',
  Won: 'won',
  Invoice: 'invoice',
  Paid: 'paid',
  Closed: 'closed',
};

/** Raw-статус crm -> ключ канбан-колонки. */
export function rawToKanban(raw?: string | null): string {
  const r = String(raw || '').toLowerCase();
  if (['reply', 'answered', 'replied'].includes(r)) return 'Replied';
  if (['negotiation', 'conversation', 'agree', 'agreement'].includes(r)) return 'Conversation';
  if (r === 'won') return 'Won';
  if (r === 'invoice') return 'Invoice';
  if (r === 'paid') return 'Paid';
  if (['closed', 'lost', 'archive', 'canceled', 'cancelled'].includes(r)) return 'Closed';
  return 'New'; // new / draft / sent и всё неизвестное
}

export function stageRu(s?: string | null): string {
  const key = String(s || '').toLowerCase();
  return STAGE_RU[key] ?? (s || '—');
}

const TONE_MAP: Record<string, Tone> = {
  ok: 'ok', healthy: 'ok', online: 'ok', active: 'ok', paid: 'ok', won: 'ok',
  success: 'ok', done: 'ok', completed: 'ok', approved: 'ok', sent: 'ok',
  warning: 'warn', warn: 'warn', degraded: 'warn', pending: 'warn',
  reply: 'warn', negotiation: 'warn', review: 'warn', draft: 'warn',
  error: 'err', failed: 'err', offline: 'err', refund: 'err',
  void: 'err', canceled: 'err', cancelled: 'err', lost: 'err',
  info: 'info', new: 'info', invoice: 'info', generated: 'info',
  none: 'none', n_a: 'none', na: 'none', '': 'gray',
};

export function toneFor(status?: string | null): Tone {
  const key = String(status || '').trim().toLowerCase().replace(/\s+/g, '_');
  return TONE_MAP[key] ?? 'gray';
}

export const LEVEL_RU: Record<string, string> = {
  info: 'инфо',
  warning: 'предупреждение',
  warn: 'предупреждение',
  error: 'ошибка',
  err: 'ошибка',
  debug: 'отладка',
};

export function levelTone(level?: string | null): Tone {
  const l = String(level || '').toLowerCase();
  if (['error', 'err', 'critical', 'fatal'].includes(l)) return 'err';
  if (['warning', 'warn'].includes(l)) return 'warn';
  return 'info';
}

export const ROLE_RU: Record<string, string> = {
  operator: 'Оператор',
  reviewer: 'Ревьюер',
  admin: 'Администратор',
};