import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Empty from '../components/Empty';
import Input from '../components/Input';
import Modal from '../components/Modal';
import Select from '../components/Select';
import Tabs from '../components/Tabs';
import { useToast } from '../components/Toast';
import { usePatchDeal } from '../hooks/mutations';
import { useAgents, useDeal, useOrders, usePayments } from '../hooks/queries';
import { fmtDateTime, fmtMoney } from '../lib/format';
import { stageRu, toneFor } from '../lib/status';
import type { Deal } from '../lib/types';

const STATUS_OPTIONS = ['new', 'sent', 'reply', 'negotiation', 'won', 'invoice', 'paid', 'closed'];

export default function DealDetail({ dealId, deal }: { dealId: string; deal?: Deal | null }) {
  const navigate = useNavigate();
  const { push } = useToast();
  const query = useDeal(dealId);
  const agents = useAgents();
  const orders = useOrders();
  const payments = usePayments();
  const patch = usePatchDeal();

  const [tab, setTab] = useState('overview');
  const [assignOpen, setAssignOpen] = useState(false);
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [newNote, setNewNote] = useState('');
  const [invoiceAmount, setInvoiceAmount] = useState('');
  const [newStatus, setNewStatus] = useState('');
  const [confirmStatus, setConfirmStatus] = useState('');

  const d: Deal | null = useMemo(() => {
    if (deal) return deal;
    const q = query.data;
    if (!q) return null;
    const items = (q as { items?: unknown[] }).items;
    if (Array.isArray(items) && items.length > 0) return items[0] as Deal;
    if (typeof q === 'object' && ('id' in q || 'title' in q || 'url' in q)) return q as unknown as Deal;
    return null;
  }, [deal, query.data]);

  const messages = useMemo(() => {
    const m = d?.messages;
    return Array.isArray(m) ? m : [];
  }, [d]);

  const order = useMemo(
    () => (orders.data?.rows || []).find((r) => r.url === dealId || r.url === d?.url),
    [orders, d, dealId],
  );

  const taskBrief = d?.exec_task || order?.exec_task;

  const doPatch = (body: Record<string, unknown>, okText: string) => {
    patch.mutate(
      { id: dealId, patch: body },
      {
        onSuccess: () => push('ok', okText),
        onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
      },
    );
  };

  if (!d) {
    return (
      <Empty
        text="Сделка не найдена"
        hint={`Данные по /api/deals/${encodeURIComponent(dealId)} недоступны. Возможно, API ещё расширяется.`}
      />
    );
  }

  return (
    <div className="stack">
      <div className="deal-head">
        <div>
          <h2>{d.title || d.id}</h2>
          <div className="muted mono">{dealId}</div>
        </div>
        <Badge tone={toneFor(d.stage || d.status)}>{stageRu(d.stage || d.status)}</Badge>
      </div>

      <Tabs
        tabs={[
          { id: 'overview', label: 'Overview' },
          { id: 'messages', label: 'Messages', count: messages.length },
          { id: 'tasks', label: 'Tasks' },
          { id: 'billing', label: 'Billing' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'overview' && (
        <>
          <div className="kv-grid">
            <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(d.status)}>{stageRu(d.status)}</Badge></span></div>
            <div className="kv"><span className="kv-k">Бюджет</span><span className="kv-v">{fmtMoney(d.budget)}</span></div>
            <div className="kv"><span className="kv-k">Источник</span><span className="kv-v">{d.source || '—'}</span></div>
            <div className="kv"><span className="kv-k">Клиент</span><span className="kv-v">{d.client || d.contact || '—'}</span></div>
            <div className="kv"><span className="kv-k">Ответственный</span><span className="kv-v">{d.agent || d.assigned_agent || '—'}</span></div>
            <div className="kv"><span className="kv-k">Automation score</span><span className="kv-v">{d.automation_score ?? d.score ?? '—'}</span></div>
            <div className="kv"><span className="kv-k">Обновлено</span><span className="kv-v">{fmtDateTime(d.ts)}</span></div>
            <div className="kv"><span className="kv-k">Invoice status</span><span className="kv-v"><Badge tone={toneFor(d.invoice_status)}>{d.invoice_status || '—'}</Badge></span></div>
          </div>
          {d.note && (
            <div className="note-block">
              <span className="kv-k">Заметка</span>
              <p>{d.note}</p>
            </div>
          )}
          <div className="deal-actions">
            <Button variant="primary" onClick={() => setAssignOpen(true)}>Assign agent</Button>
            <Button onClick={() => { setInvoiceAmount(String(order?.invoice?.amount ?? '')); setInvoiceOpen(true); }}>
              Create invoice
            </Button>
            <Button onClick={() => setNoteOpen(true)}>Add note</Button>
            <Select
              label="Изменить статус"
              options={STATUS_OPTIONS}
              placeholder="Статус…"
              value={newStatus}
              onChange={(e) => {
                const v = e.target.value;
                setNewStatus(v);
                if (!v) return;
                if (['won', 'paid'].includes(v)) {
                  setConfirmStatus(v);
                } else {
                  doPatch({ status: v }, `Статус изменён на ${stageRu(v)}`);
                }
                setNewStatus('');
              }}
            />
            <Button variant="ghost" onClick={() => navigate(`/monitoring?service=${encodeURIComponent(dealId)}`)}>
              Open in logs
            </Button>
          </div>
        </>
      )}

      {tab === 'messages' && (
        messages.length === 0 ? <Empty text="Нет переписки" /> : (
          <ul className="msg-list">
            {messages.map((m, i) => {
              const dir = String(m.direction || '').toLowerCase();
              const isIn = dir.includes('in');
              return (
                <li key={i} className={`msg ${isIn ? 'msg-in' : 'msg-out'}`}>
                  <div className="msg-head">
                    <Badge tone={isIn ? 'info' : 'ok'}>{isIn ? 'входящее' : 'исходящее'}</Badge>
                    <span className="muted">{m.channel || '—'} · {m.from || '—'} · {fmtDateTime(m.ts)}</span>
                  </div>
                  <div className="msg-text">{m.text || '—'}</div>
                </li>
              );
            })}
          </ul>
        )
      )}

      {tab === 'tasks' && (
        <>
          {taskBrief ? (
            <div className="kv-grid">
              <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(taskBrief.status)}>{taskBrief.status || '—'}</Badge></span></div>
              <div className="kv"><span className="kv-k">Создана</span><span className="kv-v">{fmtDateTime(taskBrief.created_at)}</span></div>
              <div className="kv"><span className="kv-k">Завершена</span><span className="kv-v">{fmtDateTime(taskBrief.done_at)}</span></div>
              <div className="kv"><span className="kv-k">Агенты</span><span className="kv-v">{(taskBrief.agents || []).join(', ') || '—'}</span></div>
            </div>
          ) : (
            <Empty text="Задач по сделке нет" />
          )}
          {d.agents_activity && d.agents_activity.length > 0 && (
            <>
              <div className="section-title">Активность агентов</div>
              <ul className="act-list">
                {d.agents_activity.map((a, i) => (
                  <li key={i}>
                    <Badge tone="info">{a.agent || a.file || 'agent'}</Badge>
                    <span>{a.action || a.text || ''}</span>
                    <span className="muted">{fmtDateTime(a.ts)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {tab === 'billing' && (
        <>
          <div className="kv-grid">
            <div className="kv"><span className="kv-k">Счёт №</span><span className="kv-v">{d.invoice?.no || order?.invoice?.no || '—'}</span></div>
            <div className="kv"><span className="kv-k">Сумма</span><span className="kv-v">{fmtMoney(d.invoice?.amount || order?.invoice?.amount)}</span></div>
            <div className="kv"><span className="kv-k">Статус счёта</span><span className="kv-v"><Badge tone={toneFor(d.invoice?.status || order?.invoice?.status)}>{d.invoice?.status || order?.invoice?.status || '—'}</Badge></span></div>
            <div className="kv"><span className="kv-k">Оплачен</span><span className="kv-v">{fmtDateTime(d.invoice?.paid_at || order?.invoice?.paid_at)}</span></div>
          </div>
          {(d.invoice?.payment_link || order?.invoice?.payment_link) && (
            <Button
              variant="primary"
              onClick={() => window.open(d.invoice?.payment_link || order?.invoice?.payment_link, '_blank')}
            >
              Ссылка на оплату
            </Button>
          )}
          <div className="section-title">История транзакций</div>
          {(payments.data?.items || []).filter((p) => p.url === dealId || p.deal === dealId).length === 0 ? (
            <Empty text="Транзакций нет" />
          ) : (
            <ul className="pay-list">
              {(payments.data?.items || [])
                .filter((p) => p.url === dealId || p.deal === dealId)
                .map((p, i) => (
                  <li key={i}>
                    <Badge tone={toneFor(p.pay_status || p.status)}>{p.pay_status || p.status || '—'}</Badge>
                    <span>{fmtMoney(p.amount)}</span>
                    <span className="muted">{p.method || '—'} · {fmtDateTime(p.paid_at || p.ts)}</span>
                  </li>
                ))}
            </ul>
          )}
        </>
      )}

      {assignOpen && (
        <Modal title="Назначить агента" onClose={() => setAssignOpen(false)}
          footer={<Button onClick={() => setAssignOpen(false)}>Отмена</Button>}>
          <div className="agent-pick">
            {(agents.data?.items || []).map((a) => (
              <button
                key={a.id}
                className="agent-pick-item"
                onClick={() => {
                  doPatch({ agent: a.id }, `Агент ${a.name || a.id} назначен`);
                  setAssignOpen(false);
                }}
              >
                <Badge tone={a.status === 'online' ? 'ok' : 'gray'}>{a.status || '—'}</Badge>
                <b>{a.name || a.id}</b>
                <span className="muted">{a.type || ''}</span>
              </button>
            ))}
            {agents.data?.items?.length === 0 && <Empty text="Список агентов пуст" />}
          </div>
        </Modal>
      )}

      {invoiceOpen && (
        <Modal title="Создать счёт" onClose={() => setInvoiceOpen(false)}
          footer={
            <>
              <Button
                variant="primary"
                loading={patch.isPending}
                onClick={() => {
                  doPatch({ status: 'won', invoice: { amount: invoiceAmount } }, 'Счёт создан, сделка переведена в Won');
                  setInvoiceOpen(false);
                }}
              >
                Создать счёт
              </Button>
              <Button onClick={() => setInvoiceOpen(false)}>Отмена</Button>
            </>
          }
        >
          <Input label="Сумма, ₽" type="number" value={invoiceAmount} onChange={(e) => setInvoiceAmount(e.target.value)} />
        </Modal>
      )}

      {noteOpen && (
        <Modal title="Добавить заметку" onClose={() => setNoteOpen(false)}
          footer={
            <>
              <Button
                variant="primary"
                loading={patch.isPending}
                onClick={() => {
                  doPatch({ note: newNote }, 'Заметка сохранена');
                  setNoteOpen(false);
                  setNewNote('');
                }}
              >
                Сохранить
              </Button>
              <Button onClick={() => setNoteOpen(false)}>Отмена</Button>
            </>
          }
        >
          <Input label="Текст заметки" value={newNote} onChange={(e) => setNewNote(e.target.value)} />
        </Modal>
      )}

      {confirmStatus && (
        <Modal
          title={`Перевести в «${stageRu(confirmStatus)}»?`}
          onClose={() => setConfirmStatus('')}
          footer={
            <>
              <Button
                variant="danger"
                loading={patch.isPending}
                onClick={() => {
                  doPatch({ status: confirmStatus }, `Статус изменён на ${stageRu(confirmStatus)}`);
                  setConfirmStatus('');
                }}
              >
                Подтвердить
              </Button>
              <Button onClick={() => setConfirmStatus('')}>Отмена</Button>
            </>
          }
        >
          {confirmStatus === 'won'
            ? 'Сделка будет переведена в Won, будет создан счёт.'
            : 'Сделка будет помечена как оплаченная.'}
        </Modal>
      )}
    </div>
  );
}