import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Card from '../components/Card';
import Empty from '../components/Empty';
import Modal from '../components/Modal';
import Table, { type Column } from '../components/Table';
import { useToast } from '../components/Toast';
import { useCancelTask, useReassignTask } from '../hooks/mutations';
import { useAgents, useTasks } from '../hooks/queries';
import { fmtDateTime, fmtDurationSec } from '../lib/format';
import { toneFor } from '../lib/status';
import type { Agent, Task } from '../lib/types';

export default function Agents() {
  const navigate = useNavigate();
  const { push } = useToast();
  const agents = useAgents();
  const tasks = useTasks();
  const cancel = useCancelTask();
  const reassign = useReassignTask();

  const [agentFilter, setAgentFilter] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Task | null>(null);
  const [reassignTarget, setReassignTarget] = useState<Task | null>(null);

  const agentList = agents.data?.items || [];
  const taskList = useMemo(
    () => (tasks.data?.items || []).filter((t) => !agentFilter || t.agent === agentFilter || t.assigned_agent === agentFilter),
    [tasks, agentFilter],
  );

  const columns: Column<Task>[] = [
    { key: 'id', header: 'Task ID', render: (t) => <span className="mono">{t.id}</span> },
    { key: 'deal', header: 'Deal', render: (t) => <span className="mono cell-clip" title={t.deal || t.deal_url || t.url}>{t.deal || t.deal_url || t.url || '—'}</span> },
    { key: 'type', header: 'Type', render: (t) => t.type || '—' },
    { key: 'agent', header: 'Assigned agent', render: (t) => t.agent || t.assigned_agent || '—' },
    { key: 'status', header: 'Статус', render: (t) => <Badge tone={toneFor(t.status)}>{t.status || '—'}</Badge> },
    { key: 'deadline', header: 'Deadline', render: (t) => (t.deadline ? fmtDateTime(t.deadline) : '—') },
    {
      key: 'quality',
      header: 'Quality gate',
      render: (t) => {
        const q = String(t.quality?.gate ?? t.quality?.status ?? 'none').toLowerCase();
        const tone = q === 'ok' || q === 'passed' ? 'ok' : q === 'failed' ? 'err' : 'gray';
        return <Badge tone={tone as 'ok' | 'err' | 'gray'}>{q || 'none'}</Badge>;
      },
    },
    {
      key: 'controls',
      header: 'Действия',
      render: (t) => (
        <div className="inline-actions">
          <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setReassignTarget(t); }}>
            Reassign
          </Button>
          <Button size="sm" variant="danger" onClick={(e) => { e.stopPropagation(); setCancelTarget(t); }}>
            Cancel
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="page">
      <DocumentTitle title="Агенты" />
      <div className="page-head">
        <h1>Агенты</h1>
        <p className="muted">Исполнители и задачи</p>
      </div>

      <div className="agent-grid">
        {agentList.length === 0 && <Empty text="Список агентов пуст" hint="Данные появятся после расширения API (/api/agents)" />}
        {agentList.map((a: Agent) => (
          <Card
            key={a.id}
            title={
              <span>
                {a.name || a.id}{' '}
                <Badge tone={String(a.status || '').toLowerCase() === 'online' ? 'ok' : 'gray'}>{a.status || '—'}</Badge>
              </span>
            }
            accent={String(a.status || '').toLowerCase() === 'online' ? 'ok' : 'gray'}
            onClick={() => setAgentFilter(agentFilter === a.id ? null : a.id)}
            className={agentFilter === a.id ? 'agent-card-active' : ''}
          >
            <div className="agent-meta">
              <div><span className="muted">Type:</span> {a.type || '—'}</div>
              <div>
                <span className="muted">Load:</span> {a.load ?? a.active_tasks ?? 0}%
                {typeof a.active_tasks === 'number' && <span className="muted"> ({a.active_tasks} задач)</span>}
              </div>
              <div><span className="muted">Среднее время:</span> {fmtDurationSec(a.avg_time)}</div>
              <div><span className="muted">Успех:</span> {a.success_rate === undefined ? '—' : `${a.success_rate}%`}</div>
            </div>
            {agentFilter === a.id && <div className="agent-filter-hint">Фильтр задач по агенту активен</div>}
          </Card>
        ))}
      </div>

      <Card
        title="Задачи"
        actions={agentFilter ? <Button variant="ghost" size="sm" onClick={() => setAgentFilter(null)}>Сбросить фильтр</Button> : undefined}
      >
        <Table
          columns={columns}
          data={taskList}
          rowKey={(t, i) => t.id || `task-${i}`}
          onRowClick={(t) => navigate(`/task/${encodeURIComponent(t.id)}`)}
          loading={tasks.isLoading}
          emptyText="Задач нет"
        />
      </Card>

      {cancelTarget && (
        <Modal
          title="Отменить задачу?"
          onClose={() => setCancelTarget(null)}
          footer={
            <>
              <Button
                variant="danger"
                loading={cancel.isPending}
                onClick={() => {
                  cancel.mutate(cancelTarget.id, {
                    onSuccess: () => push('ok', `Задача ${cancelTarget.id} отменена`),
                    onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                  });
                  setCancelTarget(null);
                }}
              >
                Отменить задачу
              </Button>
              <Button onClick={() => setCancelTarget(null)}>Назад</Button>
            </>
          }
        >
          Задача <span className="mono">{cancelTarget.id}</span> будет отменена. Действие необратимо.
        </Modal>
      )}

      {reassignTarget && (
        <Modal title={`Переназначить задачу ${reassignTarget.id}`} onClose={() => setReassignTarget(null)}
          footer={<Button onClick={() => setReassignTarget(null)}>Отмена</Button>}>
          <div className="agent-pick">
            {agentList.map((a) => (
              <button
                key={a.id}
                className="agent-pick-item"
                onClick={() => {
                  reassign.mutate(
                    { id: reassignTarget.id, agent: a.id },
                    {
                      onSuccess: () => push('ok', `Задача переназначена на ${a.name || a.id}`),
                      onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                    },
                  );
                  setReassignTarget(null);
                }}
              >
                <Badge tone={String(a.status || '').toLowerCase() === 'online' ? 'ok' : 'gray'}>{a.status || '—'}</Badge>
                <b>{a.name || a.id}</b>
                <span className="muted">{a.type || ''}</span>
              </button>
            ))}
            {agentList.length === 0 && <Empty text="Нет агентов для переназначения" />}
          </div>
        </Modal>
      )}
    </div>
  );
}