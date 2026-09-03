import { useMemo, useState } from 'react';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Card from '../components/Card';
import Empty from '../components/Empty';
import Input from '../components/Input';
import Modal from '../components/Modal';
import Select from '../components/Select';
import Table, { type Column } from '../components/Table';
import Tabs from '../components/Tabs';
import { useToast } from '../components/Toast';
import { useFilterDecision } from '../hooks/mutations';
import { useHealth, usePendingFilter, useReplies, useSettings } from '../hooks/queries';
import { fmtDateTime, fmtDurationSec, fmtNumber } from '../lib/format';
import { toneFor } from '../lib/status';
import type { PendingFilter, Reply } from '../lib/types';

// ---------- Вкладка «Ручное ревью» ----------

function ReviewTab() {
  const { data, isLoading } = usePendingFilter();
  const decision = useFilterDecision();
  const { push } = useToast();
  const [editing, setEditing] = useState<string | null>(null);
  const [note, setNote] = useState('');

  const items = data?.items || [];

  const submit = (order: string, d: 'accept' | 'reject', withNote: string) => {
    decision.mutate(
      { order, decision: d, note: withNote || undefined },
      {
        onSuccess: () => push('ok', `Решение «${d}» по заказу отправлено`),
        onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
      },
    );
  };

  const columns: Column<PendingFilter>[] = [
    { key: 'order', header: 'Order', render: (r) => <span className="mono cell-clip" title={r.order || r.url}>{r.order || r.url || '—'}</span> },
    { key: 'title', header: 'Title', render: (r) => <span className="cell-clip" title={r.title}>{r.title || '—'}</span> },
    { key: 'score', header: 'Score', render: (r) => (r.score === undefined ? '—' : <Badge tone={r.score >= 2 ? 'ok' : r.score >= 1 ? 'warn' : 'err'}>{r.score}</Badge>) },
    {
      key: 'reasons',
      header: 'Reason codes',
      render: (r) => (r.reason_codes || []).map((c) => <Badge key={c} tone="info" title={c}>{c}</Badge>),
    },
    { key: 'action', header: 'Suggested action', render: (r) => r.suggested_action || '—' },
    {
      key: 'controls',
      header: 'Действия',
      render: (r) => {
        const id = r.order || r.url || '';
        return (
          <div className="inline-actions">
            <Button size="sm" variant="success" loading={decision.isPending} onClick={(e) => { e.stopPropagation(); submit(id, 'accept', ''); }}>
              Accept
            </Button>
            <Button size="sm" variant="danger" loading={decision.isPending} onClick={(e) => { e.stopPropagation(); submit(id, 'reject', ''); }}>
              Reject
            </Button>
            <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setEditing(editing === id ? null : id); setNote(''); }}>
              Edit &amp; Accept
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <Card title="Ручное ревью" accent="warn">
      <Table
        columns={columns}
        data={items}
        rowKey={(r, i) => r.order || r.url || `idx-${i}`}
        loading={isLoading}
        emptyText="Нет заказов, ожидающих решения"
      />
      {editing && (
        <div className="review-edit">
          <Input
            label={`Заметка для ${editing}`}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Комментарий для решения"
          />
          <Button
            variant="primary"
            loading={decision.isPending}
            onClick={() => { submit(editing, 'accept', note); setEditing(null); setNote(''); }}
          >
            Подтвердить с заметкой
          </Button>
          <Button variant="ghost" onClick={() => setEditing(null)}>Отмена</Button>
        </div>
      )}
    </Card>
  );
}

// ---------- Вкладка «Отклики» ----------

const KEYWORDS = ['дедлайн', 'бюджет', 'опыт', 'портфолио', 'срок', 'задача', 'проект', 'готов', 'могу', 'сделаю'];

function highlight(text: string): React.ReactNode {
  let parts: React.ReactNode[] = [text];
  KEYWORDS.forEach((kw) => {
    parts = parts.flatMap((p) => {
      if (typeof p !== 'string') return [p];
      const chunks: React.ReactNode[] = [];
      let rest = p;
      let idx = rest.toLowerCase().indexOf(kw.toLowerCase());
      while (idx >= 0) {
        chunks.push(rest.slice(0, idx));
        chunks.push(<b key={`${kw}-${idx}`} className="hl">{rest.slice(idx, idx + kw.length)}</b>);
        rest = rest.slice(idx + kw.length);
        idx = rest.toLowerCase().indexOf(kw.toLowerCase());
      }
      chunks.push(rest);
      return chunks;
    });
  });
  return parts;
}

function ReplyModal({ reply, onClose }: { reply: Reply; onClose: () => void }) {
  const { push } = useToast();
  return (
    <Modal
      title={<span>Отклик <span className="mono">{reply.id}</span></span>}
      onClose={onClose}
      width={760}
      footer={
        <div className="modal-foot-btns">
          <Button onClick={() => push('warn', 'Resend для отклика недоступен — доступна только повторная генерация')}>
            Resend (заглушка)
          </Button>
          <Button variant="danger" onClick={() => push('warn', 'Disable variant: заглушка, вариант не отключён')}>
            Disable variant
          </Button>
          <Button onClick={onClose}>Закрыть</Button>
        </div>
      }
    >
      <div className="kv-grid">
        <div className="kv"><span className="kv-k">Заказ</span><span className="kv-v mono cell-clip">{reply.order || reply.order_url || '—'}</span></div>
        <div className="kv"><span className="kv-k">Модель</span><span className="kv-v">{reply.model || '—'}</span></div>
        <div className="kv"><span className="kv-k">Вариант</span><span className="kv-v">{reply.variant || '—'}</span></div>
        <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(reply.status)}>{reply.status || '—'}</Badge></span></div>
        <div className="kv"><span className="kv-k">Токены</span><span className="kv-v">{fmtNumber(reply.tokens)}</span></div>
        <div className="kv"><span className="kv-k">Латентность</span><span className="kv-v">{fmtDurationSec(reply.latency_ms ? reply.latency_ms / 1000 : undefined)}</span></div>
        <div className="kv"><span className="kv-k">Создан</span><span className="kv-v">{fmtDateTime(reply.ts)}</span></div>
        <div className="kv"><span className="kv-k">Response rate</span><span className="kv-v">{reply.response_rate === undefined ? '—' : `${reply.response_rate}%`}</span></div>
      </div>
      <div className="section-title">Prompt</div>
      <pre className="pre-block">{highlight(reply.prompt || '—')}</pre>
      <div className="section-title">Response</div>
      <pre className="pre-block">{highlight(reply.response || '—')}</pre>
    </Modal>
  );
}

function RepliesTab() {
  const { data, isLoading } = useReplies();
  const [selected, setSelected] = useState<Reply | null>(null);
  const items = data?.items || [];

  const metrics = useMemo(() => {
    const n = items.length;
    const avgLat = items.length ? items.reduce((s, r) => s + (r.latency_ms || 0), 0) / items.length : 0;
    const tokens = items.reduce((s, r) => s + (r.tokens || 0), 0);
    const byVariant: Record<string, { total: number; sent: number }> = {};
    items.forEach((r) => {
      const v = r.variant || '?';
      byVariant[v] = byVariant[v] || { total: 0, sent: 0 };
      byVariant[v].total += 1;
      if (r.status === 'sent') byVariant[v].sent += 1;
    });
    return { avgLat, tokens, n, byVariant };
  }, [items]);

  const columns: Column<Reply>[] = [
    { key: 'id', header: 'Reply ID', render: (r) => <span className="mono">{r.id}</span> },
    { key: 'order', header: 'Order', render: (r) => <span className="mono cell-clip" title={r.order || r.order_url}>{r.order || r.order_url || '—'}</span> },
    { key: 'model', header: 'Model', render: (r) => r.model || '—' },
    { key: 'variant', header: 'Вариант', render: (r) => <Badge tone={r.variant === 'B' ? 'info' : 'gray'}>{r.variant || '—'}</Badge> },
    { key: 'status', header: 'Статус', render: (r) => <Badge tone={toneFor(r.status)}>{r.status || '—'}</Badge> },
    { key: 'rate', header: 'Response rate', render: (r) => (r.response_rate === undefined ? '—' : `${r.response_rate}%`) },
    { key: 'lat', header: 'Время', render: (r) => (r.latency_ms ? fmtDurationSec(r.latency_ms / 1000) : '—') },
  ];

  return (
    <div className="stack">
      <div className="kpi-grid kpi-grid-4">
        <Card className="kpi" accent="info"><div className="kpi-label">Откликов</div><div className="kpi-value">{metrics.n}</div></Card>
        <Card className="kpi" accent="warn"><div className="kpi-label">Среднее время генерации</div><div className="kpi-value">{fmtDurationSec(metrics.avgLat / 1000)}</div></Card>
        <Card className="kpi" accent="ok"><div className="kpi-label">Токены (всего)</div><div className="kpi-value">{fmtNumber(metrics.tokens)}</div></Card>
        <Card className="kpi" accent="blue"><div className="kpi-label">Конверсия по вариантам</div><div className="kpi-value">
          {Object.entries(metrics.byVariant).map(([v, m]) => (
            <span key={v} className="variant-pct">{v}: {m.total ? Math.round((m.sent * 100) / m.total) : 0}%</span>
          ))}
        </div></Card>
      </div>
      <Card title="Отклики" accent="info">
        <Table
          columns={columns}
          data={items}
          rowKey={(r) => r.id}
          onRowClick={setSelected}
          loading={isLoading}
          emptyText="Откликов пока нет"
        />
      </Card>
      {selected && <ReplyModal reply={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

// ---------- Вкладка «Настройки LLM» ----------

interface LlmSettingsState {
  model: string;
  abEnabled: boolean;
  maxTokens: string;
  temperature: string;
  safeMode: boolean;
  fallback: string;
}

function SettingsTab() {
  const settings = useSettings();
  const health = useHealth();
  const { push } = useToast();

  const executors = settings.data?.config?.executors || {};
  const lm = executors.lmstudio || {};
  const models = health.data?.models || [];

  const [local, setLocal] = useState<LlmSettingsState | null>(null);
  const dirty = !!local;

  const live: LlmSettingsState = {
    model: lm.model || '—',
    abEnabled: true,
    maxTokens: String(lm.max_tokens ?? 2000),
    temperature: String(lm.temperature ?? 0.3),
    safeMode: true,
    fallback: 'default',
  };
  const state = local ?? live;

  return (
    <Card
      title="Настройки LLM (только просмотр)"
      accent="info"
      actions={
        dirty ? <Badge tone="warn">изменения не сохранены</Badge> : <Badge tone="ok">значения из конфига</Badge>
      }
    >
      <div className="form-grid">
        <Select
          label="Модель (executors.lmstudio)"
          options={models.length ? models : [lm.model || 'omnicoder-qwen3.5-9b-claude-4.6-opus-uncensored-v2']}
          value={state.model}
          onChange={(e) => setLocal((s) => ({ ...(s ?? live), model: e.target.value }))}
        />
        <Input
          label="Max tokens"
          type="number"
          value={state.maxTokens}
          onChange={(e) => setLocal((s) => ({ ...(s ?? live), maxTokens: e.target.value }))}
        />
        <Input
          label="Temperature"
          type="number"
          step="0.1"
          value={state.temperature}
          onChange={(e) => setLocal((s) => ({ ...(s ?? live), temperature: e.target.value }))}
        />
        <Select
          label="Fallback-шаблон"
          options={['default', 'technical', 'short', 'formal']}
          value={state.fallback}
          onChange={(e) => setLocal((s) => ({ ...(s ?? live), fallback: e.target.value }))}
        />
      </div>
      <div className="switch-row">
        <label className="switch">
          <input
            type="checkbox"
            checked={state.abEnabled}
            aria-label="A/B-тестирование вариантов отклика"
            aria-checked={state.abEnabled ? 'true' : 'false'}
            onChange={(e) => setLocal((s) => ({ ...(s ?? live), abEnabled: e.target.checked }))}
          />
          <span>A/B-тестирование вариантов отклика</span>
        </label>
        <label className="switch">
          <input
            type="checkbox"
            checked={state.safeMode}
            aria-label="Safe mode (проверка перед отправкой)"
            aria-checked={state.safeMode ? 'true' : 'false'}
            onChange={(e) => setLocal((s) => ({ ...(s ?? live), safeMode: e.target.checked }))}
          />
          <span>Safe mode (проверка перед отправкой)</span>
        </label>
      </div>
      <div className="note-block muted">
        API находится в режиме только для чтения. Правки хранятся локально в сессии и не применяются к конфигу.
      </div>
      {dirty && (
        <div className="review-actions">
          <Button variant="primary" onClick={() => { setLocal(null); push('info', 'Локальные правки сброшены'); }}>
            Сбросить правки
          </Button>
        </div>
      )}
      <div className="section-title">Доступные модели (из /health)</div>
      {models.length === 0 ? <Empty text="Список моделей недоступен" /> : (
        <ul className="model-list">
          {models.map((m) => (
            <li key={m}>
              <Badge tone={m === state.model ? 'ok' : 'gray'}>{m}</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function LLMFilter() {
  const [tab, setTab] = useState('review');
  return (
    <div className="page">
      <DocumentTitle title="LLM и фильтр" />
      <div className="page-head">
        <h1>LLM и фильтр</h1>
        <p className="muted">Ревью отбора, отклики и настройки генерации</p>
      </div>
      <Tabs
        tabs={[
          { id: 'review', label: 'Ручное ревью' },
          { id: 'replies', label: 'Отклики' },
          { id: 'settings', label: 'Настройки LLM' },
        ]}
        active={tab}
        onChange={setTab}
      />
      {tab === 'review' && <ReviewTab />}
      {tab === 'replies' && <RepliesTab />}
      {tab === 'settings' && <SettingsTab />}
    </div>
  );
}