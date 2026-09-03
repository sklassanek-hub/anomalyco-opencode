import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Card from '../components/Card';
import Modal from '../components/Modal';
import Table, { type Column } from '../components/Table';
import { useToast } from '../components/Toast';
import { useMarkInvoicePaid, useResendInvoice } from '../hooks/mutations';
import { useInvoices, useLogs, usePayments, useSettings } from '../hooks/queries';
import { fmtDateTime, fmtMoney } from '../lib/format';
import { toneFor } from '../lib/status';
import type { InvoiceItem, PaymentItem } from '../lib/types';

export default function Billing() {
  const navigate = useNavigate();
  const { push } = useToast();
  const invoices = useInvoices();
  const payments = usePayments();
  const settings = useSettings();
  const webhookLogs = useLogs({ service: 'api', limit: 10 });

  const resend = useResendInvoice();
  const markPaid = useMarkInvoicePaid();

  const [confirmResend, setConfirmResend] = useState<InvoiceItem | null>(null);
  const [confirmPaid, setConfirmPaid] = useState<InvoiceItem | null>(null);
  const [linkTarget, setLinkTarget] = useState<InvoiceItem | null>(null);

  const yoomoney = settings.data?.config?.payment?.methods?.yoomoney;

  const invColumns: Column<InvoiceItem>[] = [
    {
      key: 'no',
      header: 'Invoice ID',
      render: (i) => (
        <a className="mono link" onClick={(e) => { e.stopPropagation(); navigate(`/invoice/${encodeURIComponent(i.id || i.no || '')}`); }}>
          {i.no || i.id || '—'}
        </a>
      ),
    },
    { key: 'deal', header: 'Deal', render: (i) => <span className="mono cell-clip" title={i.url || i.deal}>{i.url || i.deal || '—'}</span> },
    { key: 'amount', header: 'Сумма', render: (i) => fmtMoney(i.amount) },
    { key: 'status', header: 'Статус', render: (i) => <Badge tone={toneFor(i.status)}>{i.status || '—'}</Badge> },
    { key: 'created', header: 'Created at', render: (i) => fmtDateTime(i.created_at) },
    { key: 'method', header: 'Payment method', render: (i) => i.method || '—' },
    { key: 'retries', header: 'Retries', render: () => '—' },
    {
      key: 'controls',
      header: 'Действия',
      render: (i) => (
        <div className="inline-actions">
          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setConfirmResend(i); }}>Resend</Button>
          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setLinkTarget(i); }}>Open payment link</Button>
          <Button size="sm" variant="success" onClick={(e) => { e.stopPropagation(); setConfirmPaid(i); }}>Mark as paid</Button>
        </div>
      ),
    },
  ];

  const payColumns: Column<PaymentItem>[] = [
    { key: 'type', header: 'Событие', render: (p) => <Badge tone={p.pay_status === 'paid' ? 'ok' : p.pay_status === 'refund' ? 'err' : 'warn'}>{p.pay_status || p.status || '—'}</Badge> },
    { key: 'amount', header: 'Сумма', render: (p) => fmtMoney(p.amount) },
    { key: 'time', header: 'Время', render: (p) => fmtDateTime(p.paid_at || p.ts) },
    { key: 'deal', header: 'Сделка', render: (p) => <span className="mono cell-clip" title={p.url || p.deal}>{p.url || p.deal || '—'}</span> },
    { key: 'method', header: 'Метод', render: (p) => p.method || '—' },
  ];

  return (
    <div className="page">
      <DocumentTitle title="Оплата" />
      <div className="page-head">
        <h1>Оплата</h1>
        <p className="muted">Счета и платежи</p>
      </div>

      <Card title="Счета" accent="info">
        <Table
          columns={invColumns}
          data={invoices.data?.items || []}
          rowKey={(i, idx) => i.no || i.id || `inv-${idx}`}
          loading={invoices.isLoading}
          emptyText="Счетов нет"
        />
      </Card>

      <Card title="Платежи" accent="ok">
        <Table
          columns={payColumns}
          data={payments.data?.items || []}
          rowKey={(p, idx) => `${p.url}-${p.paid_at || p.ts || idx}`}
          loading={payments.isLoading}
          emptyText="Платежей нет"
        />
      </Card>

      <Card title="Интеграция: ЮMoney" accent="info">
        <div className="kv-grid">
          <div className="kv">
            <span className="kv-k">Статус</span>
            <span className="kv-v">
              <Badge tone={yoomoney?.enabled ? 'ok' : 'gray'}>{yoomoney?.enabled ? 'включён' : 'выключен'}</Badge>
            </span>
          </div>
          <div className="kv"><span className="kv-k">Примечание</span><span className="kv-v">{yoomoney?.note || '—'}</span></div>
          <div className="kv"><span className="kv-k">Latency</span><span className="kv-v">n/a</span></div>
        </div>
        <div className="section-title">Последние события webhook (service=api)</div>
        <ul className="alert-list">
          {(webhookLogs.data?.logs || webhookLogs.data?.items || []).length === 0 ? (
            <li className="muted">Событий нет</li>
          ) : (
            (webhookLogs.data?.logs || webhookLogs.data?.items || []).slice(0, 10).map((l, i) => (
              <li key={i} className="alert-item">
                <Badge tone={toneFor(l.level)}>{l.level || 'info'}</Badge>
                <span className="alert-text">{l.text || l.msg || '—'}</span>
                <span className="alert-ts">{fmtDateTime(l.ts)}</span>
              </li>
            ))
          )}
        </ul>
      </Card>

      {confirmResend && (
        <Modal
          title={`Переотправить счёт ${confirmResend.no || confirmResend.id}?`}
          onClose={() => setConfirmResend(null)}
          footer={
            <>
              <Button
                variant="primary"
                loading={resend.isPending}
                onClick={() => {
                  resend.mutate(confirmResend.id || confirmResend.no || '', {
                    onSuccess: () => push('ok', `Счёт ${confirmResend.no} переотправлен`),
                    onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                  });
                  setConfirmResend(null);
                }}
              >
                Переотправить
              </Button>
              <Button onClick={() => setConfirmResend(null)}>Отмена</Button>
            </>
          }
        >
          Счёт будет отправлен клиенту повторно.
        </Modal>
      )}

      {confirmPaid && (
        <Modal
          title={`Отметить счёт ${confirmPaid.no || confirmPaid.id} оплаченным?`}
          onClose={() => setConfirmPaid(null)}
          footer={
            <>
              <Button
                variant="success"
                loading={markPaid.isPending}
                onClick={() => {
                  markPaid.mutate(confirmPaid.id || confirmPaid.no || '', {
                    onSuccess: () => push('ok', `Счёт ${confirmPaid.no} отмечен оплаченным`),
                    onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                  });
                  setConfirmPaid(null);
                }}
              >
                Отметить оплаченным
              </Button>
              <Button onClick={() => setConfirmPaid(null)}>Отмена</Button>
            </>
          }
        >
          Сделка будет переведена в статус «Оплачено».
        </Modal>
      )}

      {linkTarget && (
        <Modal title={`Оплата счёта ${linkTarget.no || linkTarget.id}`} onClose={() => setLinkTarget(null)}
          footer={<Button onClick={() => setLinkTarget(null)}>Закрыть</Button>}>
          {linkTarget.payment_link ? (
            <Button variant="primary" onClick={() => window.open(linkTarget.payment_link, '_blank')}>
              Открыть ссылку на оплату
            </Button>
          ) : (
            <div className="note-block">
              Ссылка не предоставлена API. Реквизиты для перевода:
              <ul className="req-list">
                <li>ЮMoney кошелёк: {settings.data?.config?.payment?.wallet || '—'}</li>
                {yoomoney?.note && <li>Примечание: {yoomoney.note}</li>}
                {settings.data?.config?.payment?.methods?.card && (
                  <>
                    <li>Карта: {settings.data.config.payment.methods.card.number || '—'}</li>
                    <li>Держатель: {settings.data.config.payment.methods.card.holder || '—'}</li>
                  </>
                )}
                {settings.data?.config?.payment?.methods?.usdt?.address && (
                  <li>USDT (TRC20): {settings.data.config.payment.methods.usdt.address}</li>
                )}
              </ul>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}