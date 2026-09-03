import { useMemo } from 'react';
import DocumentTitle from '../components/DocumentTitle';
import Card from '../components/Card';
import Empty from '../components/Empty';
import { useFunnel, useInvoices, useOrders, usePayments } from '../hooks/queries';

// W14 — link to metrics_funnel.json structure
const METRICS_FUNNEL_PATH = '/state/metrics_funnel.json';

export default function FunnelMetrics() {
  const funnel = useFunnel();
  const orders = useOrders();
  const invoices = useInvoices();
  const paymentsHook = usePayments();

  const metrics = useMemo(() => {
    // Конверсия из воронки
    const counts = funnel.data?.counts || {};
    const total = funnel.data?.total || (counts.new || 0) + (counts.draft || 0) + (counts.approved || 0) + (counts.replied || 0);
    const won = counts.won || 0;
    const conversion = total > 0 ? Math.round((won / total) * 100) : 0;

    // Выручка: оплаченные счета + подтверждённые платежи
    const invoiceItems = invoices.data?.items || [];
    const paidInvoices = invoiceItems.filter((inv) => inv.status === 'paid' || !!inv.paid_at);
    const revenueInvoices = paidInvoices.reduce((sum, inv) => {
      const amount = parseFloat(String(inv.amount || '0')) || 0;
      return sum + amount;
    }, 0);

    const paymentsData = paymentsHook.data?.items || paymentsHook.data || [];
    const paymentsList = Array.isArray(paymentsData) ? paymentsData : paymentsData.items || [];
    const revenuePayments = paymentsList.reduce((sum: number, p: any) => {
      const amount = parseFloat(String(p.amount || '0')) || 0;
      return sum + amount;
    }, 0);

    const revenue = Math.round((revenueInvoices + revenuePayments) * 100) / 100;

    // Расходы: если в state/payments или config указан бюджет / расходы
    // Пробуем прочитать из config через fetch (если доступен)
    const expenses = 0; // Нет явного источника расходов в state; по умолчанию 0

    // Средний чек: средний бюджет заказов
    const rows = orders.data?.rows || [];
    const budgets = rows
      .map((r) => parseFloat(String(r.budget || '0')) || 0)
      .filter((b) => b > 0);
    const avgOrder = budgets.length > 0
      ? Math.round((budgets.reduce((a, b) => a + b, 0) / budgets.length) * 100) / 100
      : 0;

    return { conversion, revenue, expenses, avgOrder };
  }, [funnel, orders, invoices, paymentsHook]);

  return (
    <>
      <DocumentTitle title="Метрики воронки" />
      <Card title="Агрегированные метрики воронки (§14)" accent="info" aria-label="MetricsFunnel — агрегированные KPI из Orders и Payment" role="region">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
        <div aria-label="Конверсия воронки" role="region" aria-describedby="kpi-conv-label kpi-conv-value">
          <div id="kpi-conv-label" className="kpi-label">Конверсия</div>
          <div id="kpi-conv-value" className="kpi-value">{metrics.conversion}%</div>
          <div className="kpi-hint">выиграно / всего</div>
        </div>
        <div aria-label="Выручка воронки" role="region" aria-describedby="kpi-rev-label kpi-rev-value">
          <div id="kpi-rev-label" className="kpi-label">Выручка</div>
          <div id="kpi-rev-value" className="kpi-value">{metrics.revenue.toLocaleString('ru-RU')} ₽</div>
          <div className="kpi-hint">оплаченные заказы</div>
        </div>
        <div aria-label="Расходы воронки" role="region" aria-describedby="kpi-exp-label kpi-exp-value">
          <div id="kpi-exp-label" className="kpi-label">Расходы</div>
          <div id="kpi-exp-value" className="kpi-value">{metrics.expenses.toLocaleString('ru-RU')} ₽</div>
          <div className="kpi-hint">из state/ (если есть)</div>
        </div>
        <div aria-label="Средний чек воронки" role="region" aria-describedby="kpi-avg-label kpi-avg-value">
          <div id="kpi-avg-label" className="kpi-label">Средний чек</div>
          <div id="kpi-avg-value" className="kpi-value">{metrics.avgOrder.toLocaleString('ru-RU')} ₽</div>
          <div className="kpi-hint">средний бюджет заказа</div>
        </div>
      </div>
      <div style={{ marginTop: '8px', fontSize: '12px', color: '#888' }} aria-label="Sources: Orders page, Payment page, funnel state">
        Источники: <a href="/orders" aria-label="Orders">Orders</a> + <a href="/billing" aria-label="Payment">Payment</a> | config.json, state/orders.json, state/payments.json, funnel | metrics_funnel.json
      </div>
    </Card>
    </>
  );
}
