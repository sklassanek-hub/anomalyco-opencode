import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Card from '../components/Card';
import DocumentTitle from '../components/DocumentTitle';
import Empty from '../components/Empty';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';
import { useMarkInvoicePaid, useResendInvoice } from '../hooks/mutations';
import { useInvoices, usePayments, useSettings } from '../hooks/queries';
import { fmtDateTime, fmtMoney } from '../lib/format';
import { toneFor } from '../lib/status';

export default function InvoicePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { push } = useToast();
  const invoices = useInvoices();
  const payments = usePayments();
  const settings = useSettings();
  const resend = useResendInvoice();
  const markPaid = useMarkInvoicePaid();
  const [confirmPaid, setConfirmPaid] = useState(false);

  const invoice = useMemo(() => {
    const items = invoices.data?.items || [];
    const decoded = decodeURIComponent(id || '');
    return items.find((i) => i.no === decoded || i.id === decoded) || null;
  }, [invoices, id]);

  const linkedPayments = useMemo(
    () => (payments.data?.items || []).filter((p) => p.url === invoice?.url || p.deal === invoice?.deal),
    [payments, invoice],
  );

  if (!invoice) {
    return (
      <div className="page">
        <DocumentTitle title="Счет" />
        <Empty text="Счёт не найден" hint={`Счёт ${id} не найден в /api/invoices`} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Счёт <span className="mono">{invoice.no || invoice.id}</span></h1>
        <p className="muted">
          <Badge tone={toneFor(invoice.status)}>{invoice.status || '—'}</Badge>
          {' '}· <span className="mono">{invoice.url || invoice.deal || '—'}</span>
        </p>
      </div>

      <Card title="Детали счёта" accent="info">
        <div className="kv-grid">
          <div className="kv"><span className="kv-k">Номер</span><span className="kv-v">{invoice.no || '—'}</span></div>
          <div className="kv"><span className="kv-k">Сумма</span><span className="kv-v">{fmtMoney(invoice.amount)}</span></div>
          <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(invoice.status)}>{invoice.status || '—'}</Badge></span></div>
          <div className="kv"><span className="kv-k">Метод</span><span className="kv-v">{invoice.method || '—'}</span></div>
          <div className="kv"><span className="kv-k">Создан</span><span className="kv-v">{fmtDateTime(invoice.created_at)}</span></div>
          <div className="kv"><span className="kv-k">Отправлен</span><span className="kv-v">{fmtDateTime(invoice.sent_at)}</span></div>
          <div className="kv"><span className="kv-k">Оплачен</span><span className="kv-v">{fmtDateTime(invoice.paid_at)}</span></div>
          <div className="kv"><span className="kv-k">Название</span><span className="kv-v">{invoice.title || '—'}</span></div>
        </div>
        <div className="deal-actions">
          <Button variant="primary" onClick={() => {
            resend.mutate(invoice.id || invoice.no || '', {
              onSuccess: () => push('ok', `Счёт ${invoice.no} переотправлен`),
              onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
            });
          }}>
            Resend
          </Button>
          {invoice.payment_link ? (
            <Button onClick={() => window.open(invoice.payment_link, '_blank')}>Open payment link</Button>
          ) : (
            <Button onClick={() => push('info', `Реквизиты: кошелёк ЮMoney ${settings.data?.config?.payment?.wallet || '—'}`)}>
              Open payment link
            </Button>
          )}
          <Button variant="success" onClick={() => setConfirmPaid(true)}>Mark as paid</Button>
          <Button variant="ghost" onClick={() => invoice.url && navigate(`/deal/${encodeURIComponent(invoice.url)}`)}>
            Открыть сделку
          </Button>
        </div>
      </Card>

      <Card title="Транзакции по счёту" accent="ok">
        {linkedPayments.length === 0 ? (
          <Empty text="Транзакций нет" />
        ) : (
          <ul className="pay-list">
            {linkedPayments.map((p, i) => (
              <li key={i}>
                <Badge tone={toneFor(p.pay_status || p.status)}>{p.pay_status || p.status || '—'}</Badge>
                <span>{fmtMoney(p.amount)}</span>
                <span className="muted">{p.method || '—'} · {fmtDateTime(p.paid_at || p.ts)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {confirmPaid && (
        <Modal
          title={`Отметить счёт ${invoice.no} оплаченным?`}
          onClose={() => setConfirmPaid(false)}
          footer={
            <>
              <Button
                variant="success"
                loading={markPaid.isPending}
                onClick={() => {
                  markPaid.mutate(invoice.id || invoice.no || '', {
                    onSuccess: () => push('ok', `Счёт ${invoice.no} отмечен оплаченным`),
                    onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                  });
                  setConfirmPaid(false);
                }}
              >
                Отметить оплаченным
              </Button>
              <Button onClick={() => setConfirmPaid(false)}>Отмена</Button>
            </>
          }
        >
          Сделка будет переведена в статус «Оплачено».
        </Modal>
      )}
    </div>
  );
}