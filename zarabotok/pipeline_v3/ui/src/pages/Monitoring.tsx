import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Badge from '../components/Badge';
import DocumentTitle from '../components/DocumentTitle';
import Button from '../components/Button';
import Card from '../components/Card';
import { BarChart, LineChart } from '../components/Chart';
import Empty from '../components/Empty';
import Input from '../components/Input';
import Modal from '../components/Modal';
import Select from '../components/Select';
import Table, { type Column } from '../components/Table';
import Tabs from '../components/Tabs';
import { useHealth, useLogs, useMetrics } from '../hooks/queries';
import { fmtDateTime, num, parseTs } from '../lib/format';
import { levelTone } from '../lib/status';
import type { LogEntry, MetricWorker } from '../lib/types';

// ---------- Метрики ----------

function MetricsTab() {
  const metrics = useMetrics();
  const m = metrics.data || {};

  const tp = useMemo(
    () =>
      Object.entries(m.throughput_per_stage || {}).map(([label, value]) => ({
        label,
        value: num(value),
      })),
    [m],
  );

  const latency = useMemo(() => {
    const per = m.latency_per_stage || {};
    const entries = Object.entries(per);
    return {
      p50: entries.map(([label, v]) => ({ label, value: num(v?.p50) })),
      p95: entries.map(([label, v]) => ({ label, value: num(v?.p95) })),
    };
  }, [m]);

  const kpi = m.kpi || {};
  const kpiCards = [
    { label: 'Конверсия откликов', value: kpi.conversion_percent ?? kpi.conversion ?? '—', suffix: '%' },
    { label: 'False positive (фильтр)', value: kpi.false_positive ?? kpi.false_positive_rate ?? '—', suffix: '%' },
    { label: 'Время до оплаты', value: kpi.time_to_payment_days ?? kpi.time_to_payment ?? '—', suffix: ' дн' },
  ];

  return (
    <div className="stack">
      <DocumentTitle title="Мониторинг" />
      <div className="kpi-grid kpi-grid-3">
        {kpiCards.map((k) => (
          <Card key={k.label} className="kpi" accent="info">
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{String(k.value)}{k.value !== '—' ? k.suffix : ''}</div>
          </Card>
        ))}
      </div>
      <Card title="Throughput per stage (заказов/час)" accent="ok">
        {tp.length ? <BarChart data={tp} /> : <Empty text="Нет данных throughput" />}
      </Card>
      <Card title="Latency P50 / P95 (сек)" accent="warn">
        {latency.p50.length ? (
          <LineChart series={[latency.p50, latency.p95]} seriesNames={['P50', 'P95']} formatValue={(v) => v.toFixed(1)} />
        ) : (
          <Empty text="Нет данных latency" />
        )}
      </Card>
    </div>
  );
}

// ---------- Сервисы ----------

function serviceState(s: MetricWorker | Record<string, unknown>): { status: string; tone: 'ok' | 'warn' | 'err' | 'gray' } {
  const st = String(s.status ?? 'offline').toLowerCase();
  if (['online', 'ok', 'healthy', 'running', 'active', 'up'].includes(st)) return { status: 'online', tone: 'ok' };
  if (['degraded', 'warning', 'starting', 'retry'].includes(st)) return { status: 'degraded', tone: 'warn' };
  if (['offline', 'error', 'down', 'dead', 'stopped', 'failed'].includes(st)) return { status: 'offline', tone: 'err' };
  return { status: st || 'n/a', tone: 'gray' };
}

function ServicesTab() {
  const metrics = useMetrics();
  const health = useHealth();
  const logs = useLogs({ level: 'error', limit: 200 });
  const [selected, setSelected] = useState<string | null>(null);

  const services = useMemo(() => {
    const out: { name: string; status?: string; uptime?: number; error_rate?: number }[] = [];
    (metrics.data?.workers || []).forEach((w) => out.push(w));
    const h = health.data || {};
    Object.entries(h.workers || {}).forEach(([name, st]) => {
      if (!out.some((s) => s.name === name)) out.push({ name, status: String(st) });
    });
    Object.entries(h.services || {}).forEach(([name, st]) => {
      if (!out.some((s) => s.name === name)) out.push({ name, status: String(st) });
    });
    (['storage', 'lmstudio', 'email', 'socks'] as const).forEach((n) => {
      if (!out.some((s) => s.name === n)) out.push({ name: n, status: 'n/a' });
    });
    return out;
  }, [metrics, health]);

  const errCount = useMemo(() => {
    const map: Record<string, number> = {};
    (logs.data?.logs || logs.data?.items || []).forEach((l) => {
      const svc = l.service || 'unknown';
      map[svc] = (map[svc] || 0) + 1;
    });
    return map;
  }, [logs]);

  const lastIncident = useMemo(() => {
    const map: Record<string, LogEntry> = {};
    (logs.data?.logs || logs.data?.items || []).forEach((l) => {
      const svc = l.service || 'unknown';
      if (!map[svc] || (parseTs(l.ts) || 0) > (parseTs(map[svc].ts) || 0)) map[svc] = l;
    });
    return map;
  }, [logs]);

  const columns: Column<(typeof services)[number]>[] = [
    { key: 'name', header: 'Сервис', render: (s) => <b>{s.name}</b> },
    { key: 'status', header: 'Статус', render: (s) => { const st = serviceState(s); return <Badge tone={st.tone}>{st.status}</Badge>; } },
    { key: 'uptime', header: 'Uptime', render: () => 'n/a' },
    { key: 'err', header: 'Error rate', render: (s) => (errCount[s.name] ? `${errCount[s.name]} err` : '0') },
    {
      key: 'incident',
      header: 'Last incident',
      render: (s) => (
        lastIncident[s.name] ? (
          <span className="cell-clip" title={lastIncident[s.name].text || lastIncident[s.name].msg}>
            {lastIncident[s.name].text || lastIncident[s.name].msg || '—'}
          </span>
        ) : '—'
      ),
    },
  ];

  return (
    <Card title="Сервисы" accent="info">
      <Table
        columns={columns}
        data={services}
        rowKey={(s, i) => s.name || `svc-${i}`}
        onRowClick={(s) => setSelected(s.name)}
        emptyText="Нет данных о сервисах"
      />
      {selected && (
        <Modal title={`Сервис: ${selected}`} onClose={() => setSelected(null)} width={720}>
          <div className="kv-grid">
            <div className="kv"><span className="kv-k">Uptime</span><span className="kv-v">n/a</span></div>
            <div className="kv"><span className="kv-k">Ошибок (в выборке)</span><span className="kv-v">{errCount[selected] ?? 0}</span></div>
          </div>
          <div className="section-title">Последние ошибки</div>
          <ul className="alert-list">
            {(logs.data?.logs || logs.data?.items || [])
              .filter((l) => (l.service || 'unknown') === selected)
              .slice(0, 10)
              .map((l, i) => (
                <li key={i} className="alert-item">
                  <Badge tone={levelTone(l.level)}>{l.level || 'error'}</Badge>
                  <span className="alert-text">{l.text || l.msg || '—'}</span>
                  <span className="alert-ts">{fmtDateTime(l.ts)}</span>
                </li>
              ))}
          </ul>
        </Modal>
      )}
    </Card>
  );
}

// ---------- Логи ----------

function LogsTab({ initialService }: { initialService?: string }) {
  const navigate = useNavigate();
  const [service, setService] = useState(initialService || '');
  const [level, setLevel] = useState('');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState<LogEntry | null>(null);

  const logs = useLogs({ service: service || undefined, level: level || undefined, limit: 200 });

  const services = useMemo(() => {
    const s = new Set((logs.data?.logs || logs.data?.items || []).map((l) => l.service || '').filter(Boolean));
    return Array.from(s).sort();
  }, [logs]);

  const rows = useMemo(() => {
    const all = logs.data?.logs || logs.data?.items || [];
    const q = search.trim().toLowerCase();
    if (!q) return all;
    return all.filter((l) => `${l.text || ''} ${l.msg || ''} ${l.trace_id || ''}`.toLowerCase().includes(q));
  }, [logs, search]);

  const columns: Column<LogEntry>[] = [
    { key: 'ts', header: 'Время', render: (l) => fmtDateTime(l.ts) },
    { key: 'service', header: 'Сервис', render: (l) => <Badge tone="info">{l.service || '—'}</Badge> },
    { key: 'level', header: 'Уровень', render: (l) => <Badge tone={levelTone(l.level)}>{l.level || '—'}</Badge> },
    { key: 'text', header: 'Сообщение', render: (l) => <span className="cell-clip" title={l.text || l.msg}>{l.text || l.msg || '—'}</span> },
  ];

  const dealLink = (l: LogEntry): string | null => {
    if (!l.text && !l.msg) return null;
    const all = `${l.text || ''} ${l.msg || ''}`;
    const m = all.match(/https?:\/\/[^\s"']+/);
    return m ? m[0] : null;
  };

  return (
    <Card
      title="Логи"
      accent={rows.some((l) => ['error', 'err', 'fatal'].includes(String(l.level || '').toLowerCase())) ? 'err' : 'info'}
    >
      <div className="filter-bar">
        <Select label="Сервис" options={services} placeholder="Все сервисы" value={service} onChange={(e) => setService(e.target.value)} />
        <Select
          label="Уровень"
          options={['info', 'warning', 'error', 'debug']}
          placeholder="Все уровни"
          value={level}
          onChange={(e) => setLevel(e.target.value)}
        />
        <Input label="Поиск по тексту" placeholder="напр. scanner" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>
      <Table
        columns={columns}
        data={rows}
        rowKey={(l, i) => `${l.ts}-${i}`}
        onRowClick={setDetail}
        loading={logs.isLoading}
        emptyText="Логов нет"
      />
      {detail && (
        <Modal title="Запись лога" onClose={() => setDetail(null)} width={760}>
          <div className="kv-grid">
            <div className="kv"><span className="kv-k">Время</span><span className="kv-v">{fmtDateTime(detail.ts)}</span></div>
            <div className="kv"><span className="kv-k">Сервис</span><span className="kv-v"><Badge tone="info">{detail.service || '—'}</Badge></span></div>
            <div className="kv"><span className="kv-k">Уровень</span><span className="kv-v"><Badge tone={levelTone(detail.level)}>{detail.level || '—'}</Badge></span></div>
            <div className="kv"><span className="kv-k">trace_id</span><span className="kv-v mono">{detail.trace_id || '—'}</span></div>
          </div>
          <div className="section-title">Текст</div>
          <pre className="pre-block">{detail.text || detail.msg || '—'}</pre>
          {(detail.links ?? []).length > 0 && (
            <>
              <div className="section-title">Ссылки</div>
              <ul className="req-list">
                {(detail.links ?? []).map((l) => (
                  <li key={l}><a className="link" href={l} target="_blank" rel="noreferrer">{l}</a></li>
                ))}
              </ul>
            </>
          )}
          {dealLink(detail) && (
            <div className="modal-foot">
              <Button variant="primary" onClick={() => navigate(`/deal/${encodeURIComponent(dealLink(detail) || '')}`)}>
                Открыть сделку по ссылке
              </Button>
            </div>
          )}
        </Modal>
      )}
    </Card>
  );
}

export default function Monitoring() {
  const [params] = useSearchParams();
  const initialService = params.get('service') || undefined;
  const [tab, setTab] = useState('metrics');

  const tabs = [
    { id: 'metrics', label: 'Метрики' },
    { id: 'services', label: 'Сервисы' },
    { id: 'logs', label: 'Логи' },
  ];

  return (
    <div className="page">
      <div className="page-head">
        <h1>Мониторинг</h1>
        <p className="muted">{initialService ? `Фильтр по сервису: ${initialService}` : 'Состояние системы'}</p>
      </div>
      <Tabs tabs={tabs} active={tab} onChange={setTab} />
      {tab === 'metrics' && <MetricsTab />}
      {tab === 'services' && <ServicesTab />}
      {tab === 'logs' && <LogsTab initialService={initialService} />}
    </div>
  );
}