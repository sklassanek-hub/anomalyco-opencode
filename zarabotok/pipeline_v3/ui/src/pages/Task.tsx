import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Card from '../components/Card';
import Empty from '../components/Empty';
import Input from '../components/Input';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';
import { usePatchDeal } from '../hooks/mutations';
import { useTask } from '../hooks/queries';
import { post } from '../lib/api';
import { fmtDateTime, fmtNumber } from '../lib/format';
import { toneFor } from '../lib/status';

interface GateCheck {
  key: string;
  label: string;
  status: 'ok' | 'warn' | 'n/a';
  detail: string;
}

export default function TaskPage() {
  const { id } = useParams<{ id: string }>();
  const { push } = useToast();
  const patch = usePatchDeal();
  const { data: task, isLoading } = useTask(id);
  const [comment, setComment] = useState('');
  const [commentError, setCommentError] = useState('');
  const [changesOpen, setChangesOpen] = useState(false);

  const gates = useMemo<GateCheck[]>(() => {
    if (!task) return [];
    const files = task.artifacts || [];
    const totalSize = files.reduce((s, f) => s + (f.size || 0), 0);
    const ok = task.quality || {};
    return [
      { key: 'lint', label: 'Lint', status: ok.lint === 'ok' ? 'ok' : ok.lint === 'failed' ? 'warn' : 'n/a', detail: ok.lint === 'ok' ? 'пройден' : ok.lint || 'n/a' },
      { key: 'tests', label: 'Тесты', status: ok.tests === 'ok' ? 'ok' : ok.tests === 'failed' ? 'warn' : 'n/a', detail: ok.tests === 'ok' ? 'пройдены' : ok.tests || 'n/a' },
      { key: 'antiplagiarism', label: 'Антиплагиат', status: ok.antiplagiarism === 'ok' ? 'ok' : ok.antiplagiarism === 'failed' ? 'warn' : 'n/a', detail: ok.antiplagiarism === 'ok' ? 'проверен' : ok.antiplagiarism || 'n/a' },
      {
        key: 'spec',
        label: 'Соответствие ТЗ',
        status: files.length > 0 && totalSize > 0 ? 'ok' : 'warn',
        detail: files.length > 0 ? `${files.length} файлов, ${fmtNumber(totalSize)} байт` : 'артефакты не найдены',
      },
    ];
  }, [task]);

  if (isLoading) return <div className="page"><Empty text="Загрузка задачи…" /></div>;
  if (!task) {
    return (
      <div className="page">
        <Empty text="Задача не найдена" hint={`Данные по /api/tasks/${id} недоступны. Возможно, API ещё расширяется.`} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Задача <span className="mono">{task.id}</span></h1>
        <p className="muted">
          {task.title || task.type || '—'} · <Badge tone={toneFor(task.status)}>{task.status || '—'}</Badge>
        </p>
      </div>

      <Card title="Общее" accent="info">
        <div className="kv-grid">
          <div className="kv"><span className="kv-k">Тип</span><span className="kv-v">{task.type || '—'}</span></div>
          <div className="kv"><span className="kv-k">Агент</span><span className="kv-v">{task.agent || task.assigned_agent || '—'}</span></div>
          <div className="kv"><span className="kv-k">Сделка</span><span className="kv-v mono cell-clip">{task.deal || task.deal_url || task.url || '—'}</span></div>
          <div className="kv"><span className="kv-k">Создана</span><span className="kv-v">{fmtDateTime(task.created_at)}</span></div>
          <div className="kv"><span className="kv-k">Начата</span><span className="kv-v">{fmtDateTime(task.started_at)}</span></div>
          <div className="kv"><span className="kv-k">Завершена</span><span className="kv-v">{fmtDateTime(task.done_at)}</span></div>
          <div className="kv"><span className="kv-k">Дедлайн</span><span className="kv-v">{task.deadline ? fmtDateTime(task.deadline) : '—'}</span></div>
        </div>
        {task.note && (
          <div className="note-block">
            <span className="kv-k">Заметка</span>
            <p>{task.note}</p>
          </div>
        )}
      </Card>

      <Card title={`Артефакты (${(task.artifacts || []).length})`} accent="ok">
        {(task.artifacts || []).length === 0 ? (
          <Empty text="Артефакты не найдены" hint="Список может приходить в поле note задачи" />
        ) : (
          <ul className="artifact-list">
            {(task.artifacts || []).map((f, i) => (
              <li key={i}>
                <span className="mono">{f.name || '—'}</span>
                <span className="muted">{f.size ? fmtNumber(f.size) + ' байт' : '—'}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Quality Gate" accent="warn">
        <div className="gate-grid">
          {gates.map((g) => (
            <div key={g.key} className={`gate gate-${g.status === 'n/a' ? 'na' : g.status}`}>
              <div className="gate-label">{g.label}</div>
              <div className="gate-status">
                {g.status === 'ok' && <Badge tone="ok">ok</Badge>}
                {g.status === 'warn' && <Badge tone="warn">warning</Badge>}
                {g.status === 'n/a' && <Badge tone="gray">n/a</Badge>}
              </div>
              <div className="gate-detail muted">{g.detail}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Действия" accent="info">
        <div className="deal-actions">
          <Button variant="success" onClick={async () => {
            try {
              const url = task.deal || task.deal_url || task.url || '';
              if (!url) { push('warn', 'Нет URL заказа для доставки'); return; }
              await post('/api/order/' + encodeURIComponent(url) + '/deliver', {});
              push('ok', 'Доставка выполнена');
            } catch (e: any) { push('err', 'Ошибка доставки: ' + (e?.message || e)); }
          }}>
            Доставить
          </Button>
          <Button variant="success" onClick={() => push('warn', 'Отправка вручную из панели не подключена')}>
            Approve &amp; send to client
          </Button>
          <Button variant="danger" onClick={() => setChangesOpen(true)}>Request changes</Button>
          <Button
            variant="outline"
            loading={patch.isPending}
            onClick={() => {
              if (!comment.trim()) {
                setCommentError('Введите текст комментария');
                push('warn', 'Введите текст комментария');
                return;
              }
              const dealId = task.deal || task.deal_url || task.url;
              if (!dealId) {
                push('err', 'Не удалось определить сделку для комментария');
                return;
              }
              patch.mutate(
                { id: dealId, patch: { note: comment } },
                {
                  onSuccess: () => { push('ok', 'Комментарий добавлен в activity сделки'); setComment(''); },
                  onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                },
              );
            }}
          >
            Add comment
          </Button>
          <Input
            id="comment-text"
            label="Комментарий к изменениям"
            placeholder="Текст комментария"
            value={comment}
            onChange={(e) => { setComment(e.target.value); if (commentError) setCommentError(''); }}
            error={commentError}
            errorId="comment-error"
            aria-invalid={commentError ? 'true' : undefined}
            aria-describedby={commentError ? 'comment-error' : undefined}
          />
          {commentError && (
            <span id="comment-error" role="alert" className="field-error" aria-live="assertive" style={{ color: 'var(--red)', fontSize: '0.85rem', marginTop: '4px', display: 'block' }}>
              {commentError}
            </span>
          )}
        </div>
      </Card>

      {changesOpen && (
        <Modal
          title="Запросить изменения"
          onClose={() => setChangesOpen(false)}
          footer={
            <>
              <Button variant="danger" onClick={() => { push('ok', 'Запрос изменений отправлен'); setChangesOpen(false); }}>
                Отправить запрос
              </Button>
              <Button onClick={() => setChangesOpen(false)}>Отмена</Button>
            </>
          }
        >
          <Input label="Комментарий к изменениям" placeholder="Что нужно доработать" />
        </Modal>
      )}
    </div>
  );
}