// Форматирование дат/чисел/денег. Таймстампы в данных вида "2026-08-18T23:37:51+0300"
// (без двоеточия в смещении) — нормализуем перед Date.parse.

export function parseTs(ts?: string | null): number | null {
  if (!ts) return null;
  const t = String(ts).trim().replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
  const n = Date.parse(t);
  return Number.isNaN(n) ? null : n;
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export function fmtDateTime(ts?: string | null): string {
  const n = parseTs(ts);
  if (n === null) return '—';
  const d = new Date(n);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fmtDate(ts?: string | null): string {
  const n = parseTs(ts);
  if (n === null) return '—';
  const d = new Date(n);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

export function timeAgo(ts?: string | null): string {
  const n = parseTs(ts);
  if (n === null) return '—';
  const diff = Date.now() - n;
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'только что';
  if (m < 60) return `${m} мин назад`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ч назад`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} дн назад`;
  return fmtDate(ts);
}

export function fmtMoney(v?: string | number | null, currency = '₽'): string {
  if (v === undefined || v === null || v === '') return '—';
  const n = num(v);
  if (!n) return String(v);
  return `${n.toLocaleString('ru-RU')} ${currency}`;
}

export function fmtNumber(v?: string | number | null): string {
  if (v === undefined || v === null || v === '') return '—';
  const n = num(v);
  if (!n) return String(v);
  return n.toLocaleString('ru-RU');
}

export function fmtDurationSec(sec?: number | null): string {
  if (sec === undefined || sec === null || Number.isNaN(sec)) return '—';
  if (sec < 1) return `${Math.round(sec * 1000)} мс`;
  if (sec < 60) return `${sec.toFixed(1)} с`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m} мин ${s} с`;
}

export function fmtPct(v?: number | null): string {
  if (v === undefined || v === null || Number.isNaN(v)) return '—';
  return `${v}%`;
}

/** Безопасное приведение "15000", "25 000 ₽", "1.5k" к числу. */
export function num(v: unknown): number {
  if (typeof v === 'number') return Number.isFinite(v) ? v : 0;
  if (typeof v !== 'string') return 0;
  const cleaned = v
    .replace(/[^\d.,-]/g, '')
    .replace(/\s+/g, '')
    .replace(',', '.');
  const n = parseFloat(cleaned);
  return Number.isNaN(n) ? 0 : n;
}

export function firstLines(text?: string | null, n = 3): string {
  if (!text) return '—';
  const lines = text.split('\n').filter((l) => l.trim().length > 0);
  return lines.slice(0, n).join(' · ');
}