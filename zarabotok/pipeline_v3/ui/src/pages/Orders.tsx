import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Input from '../components/Input';
import Modal from '../components/Modal';
import Select from '../components/Select';
import Table, { type Column } from '../components/Table';
import { useToast } from '../components/Toast';
import { useOrder, useOrders } from '../hooks/queries';
import { fmtDateTime, fmtMoney, num } from '../lib/format';
import { stageRu, toneFor } from '../lib/status';
import type { OrderRow } from '../lib/types';

function OrderModal({ url, onClose }: { url: string; onClose: () => void }) {
  const navigate = useNavigate();
  const { push } = useToast();
  const { data, isLoading } = useOrder(url);
  const [showRaw, setShowRaw] = useState(false);

  const messages = Array.isArray(data?.messages) ? data.messages : [];
  const activity = data?.agents_activity || [];

  return (
    <Modal
      title={
        <span className="modal-title-row">
          <span className="mono">{url}</span>
          {data?.status && <Badge tone={toneFor(data.status)}>{stageRu(data.status)}</Badge>}
        </span>
      }
      onClose={onClose}
      width={760}
      footer={
        <div className="modal-foot-btns">
          <Button variant="primary" aria-label="Open deal in CRM" onClick={() => navigate(`/deal/${encodeURIComponent(url)}`)}>
            Открыть в CRM
          </Button>
          <Button aria-label="View raw JSON" onClick={() => setShowRaw(true)}>View raw</Button>
          <Button aria-label="Force re-evaluate" onClick={() => push('warn', 'Force re-evaluate: недоступно')}>Force re-evaluate</Button>
          <Button aria-label="Link order to agent via conversation" onClick={() => navigate(`/transfer?url=${encodeURIComponent(url)}`)}>AgentTransfer</Button>
          <Button aria-label="Close modal" onClick={onClose}>Закрыть</Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="modal-hint">Загрузка…</div>
      ) : (
        <div className="modal-stack">
          {data?.description && (
            <div className="kv">
              <span className="kv-k">Описание</span>
              <pre className="kv-v pre-wrap">{data.description}</pre>
            </div>
          )}
          <div className="kv-grid">
            <div className="kv"><span className="kv-k">Источник</span><span className="kv-v">{data?.source || '—'}</span></div>
            <div className="kv"><span className="kv-k">Бюджет</span><span className="kv-v">{fmtMoney(data?.budget)}</span></div>
            <div className="kv"><span className="kv-k">Score</span><span className="kv-v">{data?.score ?? '—'}</span></div>
            <div className="kv"><span className="kv-k">Канал</span><span className="kv-v">{data?.channel || '—'}</span></div>
            <div className="kv"><span className="kv-k">Контакт</span><span className="kv-v">{data?.contact || '—'}</span></div>
            <div className="kv"><span className="kv-k">Обновлён</span><span className="kv-v">{fmtDateTime(data?.ts)}</span></div>
          </div>

          <div className="kv-grid" aria-label="Conversation and auto-reply status">
            <div className="kv">
              <span className="kv-k">Conversation / Thread</span>
              <span className="kv-v"><a href={`/conversation?url=${encodeURIComponent(url)}`} aria-label="Open conversation thread">Открыть thread</a> · ключ: <code className="mono">{url?.slice(0, 40) || '—'}</code></span>
            </div>
            <div className="kv">
              <span className="kv-k">Автоответ</span>
              <span className="kv-v">{data?.auto_reply ? <Badge tone="ok">Включён</Badge> : <Badge tone="gray">Отключён</Badge>} (требуется store.load('settings').get('auto_reply') === true)</span>
            </div>
            <div className="kv">
              <span className="kv-k">Agent linkage</span>
              <span className="kv-v">{activity.length ? 'Активно (' + activity.length + ')' : '—'}</span>
            </div>
          </div>

          <div className="section-title">Сообщения ({messages.length})</div>
          {messages.length === 0 ? (
            <div className="modal-hint">Нет сообщений</div>
          ) : (
            <ul className="msg-list">
              {messages.map((m, i) => (
                <li key={i} className={`msg msg-${String(m.direction || '').toLowerCase().includes('in') ? 'in' : 'out'}`}>
                  <div className="msg-head">
                    <Badge tone={String(m.direction || '').toLowerCase().includes('in') ? 'info' : 'ok'}>
                      {String(m.direction || '').toLowerCase().includes('in') ? 'вход.' : 'исход.'}
                    </Badge>
                    <span className="muted">{m.channel || '—'} · {fmtDateTime(m.ts)}</span>
                  </div>
                  <div className="msg-text">{m.text || '—'}</div>
                </li>
              ))}
            </ul>
          )}

          {activity.length > 0 && (
            <>
              <div className="section-title">Активность агентов ({activity.length})</div>
              <ul className="act-list">
                {activity.map((a, i) => (
                  <li key={i} aria-label={`Agent action ${a.agent || a.file || 'agent'}: ${a.action || ''}`}>
                    <a href={`/agent/${encodeURIComponent(a.agent || a.file || 'unknown')}`} aria-label={`Agent ${a.agent || a.file || 'unknown'}`} onClick={(e)=>e.stopPropagation()}><Badge tone="info">{a.agent || a.file || 'agent'}</Badge></a>
                    <span>{a.action || a.text || ''}</span>
                    <span className="muted">{fmtDateTime(a.ts)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {data?.invoice && (
            <>
              <div className="section-title">Счёт</div>
              <div className="kv-grid">
                <div className="kv"><span className="kv-k">Номер</span><span className="kv-v">{data.invoice.no || '—'}</span></div>
                <div className="kv"><span className="kv-k">Сумма</span><span className="kv-v">{fmtMoney(data.invoice.amount)}</span></div>
                <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(data.invoice.status)}>{data.invoice.status || '—'}</Badge></span></div>
              </div>
            </>
          )}

          {data?.exec_task && (
            <>
              <div className="section-title">Задача выполнения</div>
              <div className="kv-grid">
                <div className="kv"><span className="kv-k">Статус</span><span className="kv-v"><Badge tone={toneFor(data.exec_task.status)}>{data.exec_task.status || '—'}</Badge></span></div>
                <div className="kv"><span className="kv-k">Создана</span><span className="kv-v">{fmtDateTime(data.exec_task.created_at)}</span></div>
                <div className="kv"><span className="kv-k">Завершена</span><span className="kv-v">{fmtDateTime(data.exec_task.done_at)}</span></div>
                <div className="kv"><span className="kv-k">Агенты</span><span className="kv-v">{(data.exec_task.agents || []).join(', ') || '—'}</span></div>
              </div>
            </>
          )}
        </div>
      )}

      {showRaw && (
        <Modal title="Raw JSON" onClose={() => setShowRaw(false)} width={900}>
          <pre className="raw-json">{JSON.stringify(data, null, 2)}</pre>
          <div className="modal-foot">
            <Button onClick={() => setShowRaw(false)}>Закрыть</Button>
          </div>
        </Modal>
      )}
    </Modal>
  );
}

export default function Orders() {
  const { data, isLoading } = useOrders();
  const [selected, setSelected] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [stage, setStage] = useState('');
  const [budgetMin, setBudgetMin] = useState('');
  const [scoreMin, setScoreMin] = useState('');
  const navigate = useNavigate();

  const sources = useMemo(() => {
    const s = new Set((data?.rows || []).map((r) => r.source || '').filter(Boolean));
    return Array.from(s).sort();
  }, [data]);

  const rows = useMemo(() => {
    return (data?.rows || []).filter((r) => {
      if (source && r.source !== source) return false;
      if (stage && r.status !== stage) return false;
      if (budgetMin && num(r.budget) < num(budgetMin)) return false;
      if (scoreMin && (r.score ?? 0) < num(scoreMin)) return false;
      return true;
    });
  }, [data, source, stage, budgetMin, scoreMin]);

  const columns: Column<OrderRow>[] = useMemo(
    () => [
      {
        key: 'url',
        header: 'Order ID',
        render: (r) => (
          <a
            className="mono link"
            href={r.url}
            target="_blank"
            rel="noreferrer"
            data-u={encodeURIComponent(r.url)}
            aria-label={`Open order ${r.url}`}
            onClick={(e) => { e.stopPropagation(); (window as any).openOrder?.(encodeURIComponent(r.url)); }}
          >
            {r.url}
          </a>
        ),
      },
      { key: 'source', header: 'Источник', render: (r) => r.source || '—' },
      { key: 'title', header: 'Title', render: (r) => <span className="cell-clip" title={r.title || ''}>{r.title || '—'}</span> },
      {
        key: 'status',
        header: 'Статус',
        render: (r) => {
          const rs = String(r.raw_status || r.status || '');
          const tone = ['new','draft'].includes(rs.toLowerCase()) ? 'warn' : rs.toLowerCase() === 'sent' ? 'ok' : 'gray';
          return (
            <span aria-label={`Status ${stageRu(r.status)}`}>
              <Badge tone={toneFor(r.status)}>{stageRu(r.status)}</Badge>
              <span className="muted" style={{marginLeft:6,fontSize:11}}>{rs || '—'}</span>
            </span>
          );
        },
      },
      {
        key: 'agent',
        header: 'Агент',
        render: (r) => {
          const agents = (r as any).agents_activity || (r as any).agent || (r as any).agents || [];
          const name = Array.isArray(agents)
            ? agents.map((a:any) => a.agent || a.file || a).filter(Boolean).join(', ')
            : (typeof agents === 'string' ? agents : '');
          if (!name) {
            return (
              <a href={`/agent/${encodeURIComponent(String((r as any).agent || ''))}`} aria-label="Link to agent assignment" onClick={(e)=>e.stopPropagation()}>
                Назначить
              </a>
            );
          }
          return (
            <a href={`/agent/${encodeURIComponent(name.split(',')[0].trim())}`} aria-label={`Agent ${name}`} onClick={(e)=>e.stopPropagation()}>
              {name}
            </a>
          );
        },
      },
      {
        key: 'lastMessage',
        header: 'Последнее сообщение',
        render: (r) => {
          const last = (r as any).last_message;
          if (last && last.text) {
            return <span className="cell-clip" title={String(last.text)}>{String(last.text).slice(0, 70) || '—'}</span>;
          }
          return r.messages != null ? `Сообщений: ${r.messages}` : '—';
        },
      },
      { key: 'budget', header: 'Бюджет', render: (r) => fmtMoney(r.budget) },
      { key: 'score', header: 'Score', render: (r) => (r.score === null || r.score === undefined ? '—' : <Badge tone={r.score >= 2 ? 'ok' : r.score >= 1 ? 'warn' : 'gray'}>{r.score}</Badge>) },
      {
        key: 'actions',
        header: 'Действия',
        render: (r) => (
          <div style={{display:'flex', gap:4, flexWrap:'wrap'}} role="group" aria-label="Quick actions">
            <Button
              size="sm"
              variant="outline"
              aria-label="Reply to order"
              onClick={(e) => { e.stopPropagation(); setSelected(r.url); }}
            >Reply</Button>
            <Button
              size="sm"
              variant="outline"
              aria-label="Assign agent to order"
              onClick={(e) => { e.stopPropagation(); navigate(`/agent/assign?url=${encodeURIComponent(r.url)}`); }}
            >Assign</Button>
            <Button
              size="sm"
              variant="outline"
              aria-label="Escalate order"
              onClick={(e) => { e.stopPropagation(); navigate(`/escalate?url=${encodeURIComponent(r.url)}`); }}
            >Escalate</Button>
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div className="page">
      <DocumentTitle title="Заказы" />
      <div className="page-head">
        <h1>Заказы</h1>
        <p className="muted">Всего: {data?.count ?? 0} · показано: {rows.length}</p>
      </div>

      <div className="filter-bar">
        <Select
          label="Источник"
          options={sources}
          placeholder="Все источники"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
        <Select
          label="Стадия"
          options={['new', 'draft', 'sent', 'reply', 'negotiation', 'won', 'invoice', 'paid', 'closed']}
          placeholder="Все стадии"
          value={stage}
          onChange={(e) => setStage(e.target.value)}
        />
        <Input label="Бюджет от, ₽" type="number" placeholder="0" value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} />
        <Input label="Score от" type="number" placeholder="0" value={scoreMin} onChange={(e) => setScoreMin(e.target.value)} />
        <Button variant="ghost" onClick={() => { setSource(''); setStage(''); setBudgetMin(''); setScoreMin(''); }}>
          Сбросить
        </Button>
        <Button variant="outline" onClick={() => navigate('/monitoring?service=scanner')}>
          Логи сканера
        </Button>
      </div>

      <Table
        columns={columns}
        data={rows}
        rowKey={(r) => r.url}
        onRowClick={(r) => setSelected(r.url)}
        loading={isLoading}
        emptyText="Заказы не найдены"
      />

      {selected && <OrderModal url={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}