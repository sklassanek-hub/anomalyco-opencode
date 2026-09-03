import { useMemo, useState } from 'react';
import DocumentTitle from '../components/DocumentTitle';
import Badge from '../components/Badge';
import Button from '../components/Button';
import DealDetail from '../components/DealDetail';
import Drawer from '../components/Drawer';
import Empty from '../components/Empty';
import KanbanBoard, { type KanbanItem } from '../components/KanbanBoard';
import Modal from '../components/Modal';
import { useToast } from '../components/Toast';
import { usePatchDeal } from '../hooks/mutations';
import { useDeals } from '../hooks/queries';
import { fmtMoney } from '../lib/format';
import { KANBAN_COLUMNS, KANBAN_TO_RAW, rawToKanban } from '../lib/status';
import type { Deal } from '../lib/types';

export default function CRM() {
  const { data, isLoading } = useDeals();
  const patch = usePatchDeal();
  const { push } = useToast();

  const [selected, setSelected] = useState<Deal | null>(null);
  const [confirm, setConfirm] = useState<{ deal: Deal; column: string } | null>(null);

  const deals = data?.items || [];

  const items: KanbanItem[] = useMemo(
    () =>
      deals.map((d) => ({
        id: d.id || d.url || 'deal',
        column: rawToKanban(d.stage || d.status || d.raw_status),
        render: () => (
          <div className="kanban-card-body">
            <div className="kanban-card-title" title={d.title || ''}>{d.title || d.id || d.url || '—'}</div>
            <div className="kanban-card-row"><span className="muted">Клиент:</span> {d.client || d.contact || '—'}</div>
            <div className="kanban-card-row"><span className="muted">Бюджет:</span> {fmtMoney(d.budget)}</div>
            <div className="kanban-card-row"><span className="muted">Источник:</span> {d.source || '—'}</div>
            <div className="kanban-card-row">
              <span className="muted">Score:</span> {d.automation_score ?? d.score ?? '—'}
              <span className="muted"> · Агент:</span> {d.agent || d.assigned_agent || '—'}
            </div>
            <div className="kanban-card-row">
              <span className="muted">Счёт:</span>{' '}
              <Badge tone={d.invoice_status ? 'info' : 'gray'}>{d.invoice_status || 'нет'}</Badge>
            </div>
          </div>
        ),
      })),
    [deals],
  );

  const onDrop = (itemId: string, column: string) => {
    const deal = deals.find((d) => d.id === itemId || d.url === itemId);
    if (!deal) return;
    const target = KANBAN_TO_RAW[column];
    const current = rawToKanban(deal.stage || deal.status);
    if (current === column) return;
    if (column === 'Won' || column === 'Paid') {
      setConfirm({ deal, column });
      return;
    }
    patch.mutate(
      { id: deal.id || deal.url || itemId, patch: { status: target } },
      {
        onSuccess: () => push('ok', `${deal.title || deal.id} → ${column}`),
        onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
      },
    );
  };

  return (
    <div className="page">
      <DocumentTitle title="CRM" />
      <div className="page-head">
        <h1>CRM</h1>
        <p className="muted">Сделки по стадиям · перетаскивайте карточки между колонками</p>
      </div>

      {isLoading ? (
        <Empty text="Загрузка сделок…" />
      ) : deals.length === 0 ? (
        <Empty text="Сделок нет" hint="Данные появятся после расширения API (/api/deals)" />
      ) : (
        <KanbanBoard
          columns={KANBAN_COLUMNS.map((c) => ({ id: c, title: c }))}
          items={items}
          onDrop={onDrop}
          onItemClick={(it) => {
            const deal = deals.find((d) => d.id === it.id || d.url === it.id);
            if (deal) setSelected(deal);
          }}
        />
      )}

      {selected && (
        <Drawer
          title={<span className="modal-title-row"><span className="mono">{selected.id || selected.url}</span><Badge tone="info">{selected.stage || selected.status || '—'}</Badge></span>}
          onClose={() => setSelected(null)}
          width={620}
        >
          <DealDetail dealId={selected.id || selected.url || ''} deal={selected} />
        </Drawer>
      )}

      {confirm && (
        <Modal
          title={`Перевести в «${confirm.column}»?`}
          onClose={() => setConfirm(null)}
          footer={
            <>
              <Button
                variant="danger"
                loading={patch.isPending}
                onClick={() => {
                  const { deal, column } = confirm;
                  const id = deal.id || deal.url || '';
                  patch.mutate(
                    { id, patch: { status: KANBAN_TO_RAW[column] } },
                    {
                      onSuccess: () => {
                        push('ok', `${deal.title || deal.id} переведена в ${column}`);
                        if (column === 'Won') push('info', 'Будет создан счёт');
                      },
                      onError: (e) => push('err', `Ошибка: ${(e as Error).message}`),
                    },
                  );
                  setConfirm(null);
                }}
              >
                Перевести
              </Button>
              <Button onClick={() => setConfirm(null)}>Отмена</Button>
            </>
          }
        >
          {confirm.column === 'Won'
            ? `Сделка «${confirm.deal.title || confirm.deal.id}» будет переведена в Won. Будет создан счёт.`
            : `Сделка «${confirm.deal.title || confirm.deal.id}» будет помечена как оплаченная.`}
        </Modal>
      )}
    </div>
  );
}