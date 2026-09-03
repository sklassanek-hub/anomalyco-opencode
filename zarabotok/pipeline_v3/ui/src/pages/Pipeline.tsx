import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Card from '../components/Card';
import { useFunnel, useMetrics } from '../hooks/queries';
import { fmtDurationSec, num } from '../lib/format';

interface Block {
  key: string;
  title: string;
  subtitle: string;
  route: string;
  stage?: string;
}

const BLOCKS: Block[] = [
  { key: 'orders', title: 'Заказы', subtitle: 'сканирование источников', route: '/orders', stage: 'new' },
  { key: 'filter', title: 'Фильтр', subtitle: 'отбор и скоринг', route: '/llm-filter', stage: 'draft' },
  { key: 'llm', title: 'LLM', subtitle: 'генерация откликов', route: '/llm-filter', stage: 'sent' },
  { key: 'crm', title: 'CRM', subtitle: 'переговоры и сделки', route: '/crm', stage: 'reply' },
  { key: 'agents', title: 'Агенты', subtitle: 'выполнение задач', route: '/agents', stage: 'negotiation' },
  { key: 'billing', title: 'Billing', subtitle: 'счета и оплата', route: '/billing', stage: 'invoice' },
];

// маппинг ребро -> пара стадий воронки для статистики переходов
const EDGE_STAGES: Record<string, [string, string]> = {
  'orders-filter': ['new', 'draft'],
  'filter-llm': ['draft', 'sent'],
  'llm-crm': ['sent', 'reply'],
  'crm-agents': ['reply', 'negotiation'],
  'agents-billing': ['won', 'invoice'],
};

export default function Pipeline() {
  const navigate = useNavigate();
  const metrics = useMetrics();
  const funnel = useFunnel();
  const [hoverEdge, setHoverEdge] = useState<string | null>(null);

  const blocks = useMemo(() => {
    return BLOCKS.map((b) => {
      const stageCount = b.stage ? funnel.data?.counts?.[b.stage] ?? 0 : 0;
      const tp =
        metrics.data?.throughput_per_stage?.[b.key] ??
        (b.stage ? metrics.data?.throughput_per_stage?.[b.stage] : undefined) ??
        stageCount;
      const latency =
        metrics.data?.latency_per_stage?.[b.key]?.p50 ??
        (b.stage ? metrics.data?.latency_per_stage?.[b.stage]?.p50 : undefined);
      const errors = metrics.data?.errors?.[b.key] ?? (b.stage ? metrics.data?.errors?.[b.stage] : undefined) ?? 0;
      return { ...b, stageCount, tp, latency, errors };
    });
  }, [metrics, funnel]);

  const edgeStat = (edge: string) => {
    const pair = EDGE_STAGES[edge];
    if (!pair) return null;
    const [from, to] = pair;
    const counts = funnel.data?.counts || {};
    const fromN = counts[from] ?? 0;
    const toN = counts[to] ?? 0;
    const stuck = Math.max(0, fromN - toN);
    const conv = fromN > 0 ? Math.round((toN * 100) / fromN) : 0;
    return { fromN, toN, stuck, conv };
  };

  const edgeLabel = (edge: string): string => {
    const s = edgeStat(edge);
    if (!s) return 'нет данных';
    return `прошло: ${s.toN}, застряло: ${s.stuck}, конверсия: ${s.conv}%`;
  };

  return (
    <div className="page">
      <DocumentTitle title="Пайплайн" />
      <div className="page-head">
        <h1>Пайплайн</h1>
        <p className="muted">Поток заказов по этапам обработки</p>
      </div>

      <Card title="Схема конвейера" accent="info">
        <div className="pipeline">
          {blocks.map((b, i) => (
            <div key={b.key} className="pipeline-node-wrap">
              <div
                className={`pipeline-node${b.errors ? ' pipeline-node-err' : ''}`}
                onClick={() => navigate(b.route)}
                role="button"
                tabIndex={0}
                aria-label={`${b.title || 'Этап'} ${b.subtitle || ''} ${b.errors > 0 ? 'ошибка ' + b.errors : ''}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(b.route);
                  }
                  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                    e.preventDefault();
                    const nodes = Array.from(document.querySelectorAll('.pipeline-node-wrap'));
                    const currentWrap = (e.target as HTMLElement).closest('.pipeline-node-wrap') as HTMLElement | null;
                    if (!currentWrap || nodes.length === 0) return;
                    const idx = nodes.indexOf(currentWrap);
                    let nextIdx = e.key === 'ArrowRight' ? idx + 1 : idx - 1;
                    if (nextIdx >= nodes.length) nextIdx = 0;
                    if (nextIdx < 0) nextIdx = nodes.length - 1;
                    const nextWrap = nodes[nextIdx] as HTMLElement;
                    const btn = nextWrap.querySelector('.pipeline-node') as HTMLElement | null;
                    if (btn) btn.focus();
                  }
                  // ArrowUp/ArrowDown to funnel rows; ArrowLeft/ArrowRight between node siblings
                  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                    e.preventDefault();
                    const funnelList = document.querySelector('.funnel-list');
                    const rows = funnelList ? Array.from(funnelList.querySelectorAll('.funnel-row')) : [];
                    const currentWrap = (e.target as HTMLElement).closest('.pipeline-node-wrap') as HTMLElement | null;
                    if (rows.length === 0) return;
                    // Focus first funnel row on ArrowDown, last on ArrowUp from nodes
                    const target = e.key === 'ArrowDown' ? rows[0] : rows[rows.length - 1];
                    (target as HTMLElement)?.focus();
                  }
                }}
              >
                <div className="pipeline-title">{b.title}</div>
                <div className="pipeline-subtitle">{b.subtitle}</div>
                <div className="pipeline-metrics">
                  <span title="Throughput">
                    <b>{num(b.tp)}</b> з/ч
                  </span>
                  <span title="Latency P50">
                    <b>{fmtDurationSec(b.latency)}</b> откл
                  </span>
                  <span title="Ошибки">
                    <Badge tone={b.errors > 0 ? 'err' : 'ok'}>{b.errors > 0 ? `${num(b.errors)} err` : '0'}</Badge>
                  </span>
                </div>
                {b.stageCount > 0 && <div className="pipeline-stage">в стадии: {b.stageCount}</div>}
              </div>
              {i < blocks.length - 1 && (
                <div
                  className="pipeline-edge"
                  onMouseEnter={() => setHoverEdge(`${b.key}-${blocks[i + 1].key}`)}
                  onMouseLeave={() => setHoverEdge(null)}
                  aria-label={`Переход от ${b.title || b.key} к ${blocks[i + 1]?.title || blocks[i + 1]?.key}`}
                  role="img"
                >
                  <span className="pipeline-arrow">→</span>
                  {hoverEdge === `${b.key}-${blocks[i + 1].key}` && (
                    <div className="edge-tooltip">{edgeLabel(`${b.key}-${blocks[i + 1].key}`)}</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card title="Конверсия по этапам (воронка)">
        <div className="funnel-list">
          {(funnel.data?.conversions || []).map((c, i) => (
            <div key={i} className="funnel-row" role="region" aria-label={`${c.from} в ${c.to}: ${c.percent}%`} onKeyDown={(e) => {
              if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                e.preventDefault();
                const list = (e.target as HTMLElement).closest('.funnel-list');
                const rows = list ? Array.from(list.querySelectorAll('.funnel-row')) : [];
                const idx = rows.indexOf(e.target as HTMLElement);
                let nextIdx = e.key === 'ArrowDown' ? idx + 1 : idx - 1;
                if (nextIdx >= rows.length) nextIdx = 0;
                if (nextIdx < 0) nextIdx = rows.length - 1;
                const next = rows[nextIdx] as HTMLElement | undefined;
                if (next) next.focus();
              }
              if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                e.preventDefault();
                const nodes = Array.from(document.querySelectorAll('.pipeline-node-wrap'));
                const active = document.activeElement as HTMLElement | null;
                const activeWrap = active ? (active.closest('.pipeline-node-wrap') as HTMLElement | null) : null;
                if (activeWrap && nodes.indexOf(activeWrap) >= 0) {
                  const idx = nodes.indexOf(activeWrap);
                  let nextIdx = e.key === 'ArrowRight' ? idx + 1 : idx - 1;
                  if (nextIdx >= nodes.length) nextIdx = 0;
                  if (nextIdx < 0) nextIdx = nodes.length - 1;
                  const nextWrap = nodes[nextIdx] as HTMLElement;
                  const btn = nextWrap.querySelector('.pipeline-node') as HTMLElement | null;
                  if (btn) btn.focus();
                } else {
                  const btn = (e.key === 'ArrowRight' ? nodes[nodes.length - 1] : nodes[0])?.querySelector('.pipeline-node') as HTMLElement | null;
                  if (btn) btn.focus();
                }
              }
            }} tabIndex={0}>
              <span className="funnel-pair">
                {c.from} → {c.to}
              </span>
              <div className="funnel-track">
                <div
                  className="funnel-fill"
                  style={{ width: `${Math.min(100, c.percent)}%` }}
                />
              </div>
              <span className="funnel-pct">{c.percent}%</span>
              <span className="funnel-counts">
                {c.count_from} → {c.count_to}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}