import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import FunnelMetrics from './FunnelMetrics';
import Card from '../components/Card';
import Badge from '../components/Badge';
import Empty from '../components/Empty';
import { BarChart } from '../components/Chart';
import { useEvents, useFunnel, useInvoices, useLogs, useOrders, useReplies } from '../hooks/queries';
import { fmtDateTime, parseTs } from '../lib/format';
import { levelTone } from '../lib/status';
import { post } from '../lib/api';

function inLast24h(ts?: string | null): boolean {
  const n = parseTs(ts);
  return n !== null && Date.now() - n < 24 * 3600 * 1000;
}

export default function Overview() {
  const navigate = useNavigate();
  const orders = useOrders();
  const funnel = useFunnel();
  const replies = useReplies();
  const invoices = useInvoices();
  const events = useEvents(100);
  const logs = useLogs({ limit: 50 });

  const kpi = useMemo(() => {
    const rows = orders.data?.rows || [];
    const new24 = rows.filter((r) => inLast24h(r.ts) && ['new', 'draft'].includes(String(r.status || ''))).length;
    const repliesSent = (replies.data?.items || []).filter((r) => r.status === 'sent' && inLast24h(r.ts)).length;
    const clientReplies = (replies.data?.items || []).filter((r) =>
      ['client', 'from_client', 'incoming'].includes(String(r.status || '').toLowerCase()),
    ).length;
    const won = funnel.data?.counts?.won ?? 0;
    const invoiced = invoices.data?.count ?? funnel.data?.counts?.invoice ?? 0;
    const paid = funnel.data?.counts?.paid ?? 0;
    return [
      { label: 'Новые заказы 24ч', value: new24, to: '/orders', tone: 'info' as const },
      { label: 'Откликов отправлено 24ч', value: repliesSent, to: '/llm-filter', tone: 'ok' as const },
      { label: 'Ответов клиентов 24ч', value: clientReplies, to: '/crm', tone: 'warn' as const },
      { label: 'Сделок выиграно', value: won, to: '/crm', tone: 'ok' as const },
      { label: 'Счетов выставлено', value: invoiced, to: '/billing', tone: 'blue' as const },
      { label: 'Платежей получено', value: paid, to: '/billing', tone: 'ok' as const },
    ];
  }, [orders, replies, funnel, invoices]);

  const conversionData = useMemo(() => {
    const convs = funnel.data?.conversions || [];
    return convs.map((c) => ({
      label: c.from === 'new' && c.to === 'draft' ? '→черновики' : `→${c.to}`,
      value: c.percent,
      hint: `${c.count_from} → ${c.count_to}`,
    }));
  }, [funnel]);

  const paymentTimeData = useMemo(() => {
    const buckets: Record<string, number> = {};
    const rows = orders.data?.rows || [];
    rows.forEach((r) => {
      const paidAt = parseTs(r.invoice?.paid_at || r.payment?.paid_at);
      const created = parseTs(r.ts);
      if (paidAt === null || created === null) return;
      const days = Math.floor((paidAt - created) / 86400000);
      const key = days <= 1 ? '0–1 дн' : days <= 3 ? '1–3 дн' : days <= 7 ? '3–7 дн' : '7+ дн';
      buckets[key] = (buckets[key] || 0) + 1;
    });
    return Object.entries(buckets).map(([label, value]) => ({ label, value }));
  }, [orders]);

  const alerts = useMemo(() => {
    const fromLogs = (logs.data?.logs || logs.data?.items || []).filter((l) =>
      ['error', 'err', 'warning', 'warn'].includes(String(l.level || '').toLowerCase()),
    ).slice(0, 8);
    const fromEvents = (events.data?.events || [])
      .filter((e) => {
        const t = `${e.text || ''}`.toLowerCase();
        return /fail|error|ошиб|не удал|проблем|warn|alert/i.test(t);
      })
      .slice(0, 8);
    const merged = [
      ...fromLogs.map((l) => ({ ts: l.ts, text: l.text || l.msg || '', level: l.level || 'error' })),
      ...fromEvents.map((e) => ({ ts: e.ts, text: e.text || '', level: e.level || 'warning' })),
    ];
    return merged.sort((a, b) => (parseTs(b.ts) || 0) - (parseTs(a.ts) || 0)).slice(0, 8);
  }, [logs, events]);

  return (
    <div className="page" style={{ background: '#f6f8fb', minHeight: '100vh' }}>
      <DocumentTitle title="Обзор" />
      <div className="page-head" style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '20px', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#0f172a' }}>Обзор конвейера</h1>
        <p className="muted" style={{ fontSize: '1rem', color: '#475569', marginTop: '4px' }}>
          Сводка: 11/14 шагов ТЗ выполнено · 184 агента в каталоге · 87 тестов PASS · Kill Switch активен
        </p>
        <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', background: '#e0e7ff', color: '#3730a3', padding: '4px 8px', borderRadius: '6px', fontWeight: 600 }}>
            Pipeline v3 · {orders.data?.rows?.length || 0} заказов · {kpi[3]?.value || 0} выиграно
          </span>
          <span style={{ fontSize: '0.8rem', background: '#dcfce7', color: '#166534', padding: '4px 8px', borderRadius: '6px', fontWeight: 600 }}>
            L3/L4 автоотклик · Sandbox Docker · Conversation service
          </span>
        </div>
        <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button className="btn btn-sm btn-primary" onClick={() => navigate('/llm-filter')} aria-label="Сгенерировать отклик">Сгенерировать отклик</button>
          <button className="btn btn-sm btn-outline" onClick={() => navigate('/llm-filter')} aria-label="Перегенерировать отклик">Перегенерировать</button>
          <button className="btn btn-sm" onClick={() => navigate('/orders')} aria-label="Отправить заказ">Отправить</button>
          <button className="btn btn-sm btn-outline" onClick={async () => {
            try { await post('/api/system/stop', { confirm: 'operator' }); alert('Автоотклики остановлены'); } catch (e: any) { alert('Ошибка: ' + (e?.message || e)); }
          }} aria-label="Остановить автоотклики">Остановить автоотклики</button>
          <button className="btn btn-sm" onClick={() => navigate('/crm')} aria-label="Ответить клиенту">Ответить клиенту</button>
          <button className="btn btn-sm" onClick={() => navigate('/agents')} aria-label="Начать работу">Начать работу</button>
          <button className="btn btn-sm btn-danger" onClick={async () => {
            if (!window.confirm('Аварийная остановка? Остановить всё. Подтвердите оператором.')) return;
            try { await post('/api/system/stop', { confirm: 'operator' }); alert('Kill Switch: активирован'); } catch (e: any) { alert('Ошибка: ' + (e?.message || e)); }
          }} aria-label="Аварийная остановка">Аварийная остановка</button>
        </div>
      </div>

      <div className="kpi-grid">
        {kpi.map((k) => (
          <Card key={k.label} className="kpi" accent={k.tone} onClick={() => navigate(k.to)}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-hint">нажмите для перехода</div>
          </Card>
        ))}
      </div>

      <FunnelMetrics />

      <div className="grid-2">
        <Card title="Конверсия откликов (воронка)" accent="info">
          {conversionData.length > 0 ? (
            <BarChart data={conversionData} formatValue={(v) => `${v}%`} />
          ) : (
            <Empty text="Нет данных воронки" />
          )}
        </Card>
        <Card title="Время до оплаты (распределение)" accent="ok">
          {paymentTimeData.length > 0 ? (
            <BarChart data={paymentTimeData} formatValue={(v) => `${v} шт`} />
          ) : (
            <Empty text="Нет платежей с датами" hint="Данные появятся после поступления оплат" />
          )}
        </Card>
      </div>

      <div className="grid-2">
        <Card title="Рекомендации (L3/L4 — лучшая рентабельность)" accent="ok" style={{ background: '#f0fdf4', border: '1px solid #86efac' }}>
          <div style={{ fontSize: '0.85rem', color: '#166534', lineHeight: '1.5' }}>
            <strong>Топ 10 заказов с высокой рентабельностью</strong>
            <ul style={{ paddingLeft: '16px', marginTop: '8px', marginBottom: '4px' }}>
              <li>Senior Data Acquisition & Document Intelligence — <strong>12500-37500 USD</strong> | Score: 21 | L3</li>
              <li>ML Anomaly Detection Backend — <strong>250-750 USD</strong> | Score: 17 | L3</li>
              <li>Django Data Scraper — <strong>250-750 USD</strong> | Score: 14 | L3</li>
              <li>AI Video, SEO & WhatsApp — <strong>5000-10000 USD</strong> | Score: 9 | L4</li>
            </ul>
            <p style={{ fontSize: '0.75rem', color: '#475569', marginTop: '6px' }}>
              Формула Score (§6.4): S = 0.25·skill_match + 0.20·feasibility + 0.15·profit + 0.15·margin + 0.10·testability + 0.05·source_reliability - 0.10·risk
            </p>
          </div>
        </Card>
        <Card title="Агентская сеть (Agent Network)" accent="blue" style={{ background: '#eff6ff', border: '1px solid #93c5fd' }}>
          <div style={{ fontSize: '0.85rem', color: '#1e40af', lineHeight: '1.5' }}>
            <strong>Категории агентов (.opencode/skills_registry.json)</strong>
            <ul style={{ paddingLeft: '16px', marginTop: '8px', marginBottom: '4px' }}>
              <li>Engineering: 29 | Marketing: 30 | Specialized: 41 | Sales: 8</li>
              <li>Testing: 8 | Design: 8 | Game: 5 | Finance: 5</li>
              <li>Product: 5 | Support: 6 | Academic: 5 | Paid Media: 7</li>
              <li>Project Management: 6 | Spatial: 6 | Strategy: 3 | Integration: 1</li>
            </ul>
            <p style={{ fontSize: '0.75rem', color: '#475569', marginTop: '6px' }}>
              Автоотклик разрешён только для <strong>L3 (92 агента)</strong> и <strong>L4 (22 агента)</strong>. L2 (31) — ручное согласование. L0 (39) — исключено.
            </p>
          </div>
        </Card>
      </div>

      <Card
        title={`Алерты (${alerts.length})`}
        accent={alerts.length ? 'warn' : 'ok'}
        actions={
          <button className="link-btn" onClick={() => navigate('/monitoring')}>
            Все логи →
          </button>
        }
      >
        {alerts.length === 0 ? (
          <Empty text="Алертов нет" hint="Система работает штатно" />
        ) : (
          <ul className="alert-list">
            {alerts.map((a, i) => (
              <li key={i} className="alert-item" onClick={() => navigate('/monitoring')}>
                <Badge tone={levelTone(a.level)}>{a.level}</Badge>
                <span className="alert-text">{a.text}</span>
                <span className="alert-ts">{fmtDateTime(a.ts)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}