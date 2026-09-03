import { useState, useRef } from 'react';

export interface KanbanColumn {
  id: string;
  title: string;
  accent?: string;
}

export interface KanbanItem {
  id: string;
  column: string;
  render: (item: KanbanItem) => React.ReactNode;
}

interface KanbanBoardProps {
  columns: KanbanColumn[];
  items: KanbanItem[];
  onDrop: (itemId: string, columnId: string) => void;
  onItemClick?: (item: KanbanItem) => void;
}

export default function KanbanBoard({ columns, items, onDrop, onItemClick }: KanbanBoardProps) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [focusCol, setFocusCol] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  const handleGridKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const colIdx = columns.findIndex((c) => c.id === focusCol);
    if (colIdx < 0) return;
    if (e.key === 'ArrowRight') {
      const next = columns[(colIdx + 1) % columns.length];
      setFocusCol(next.id);
      e.preventDefault();
    } else if (e.key === 'ArrowLeft') {
      const next = columns[(colIdx - 1 + columns.length) % columns.length];
      setFocusCol(next.id);
      e.preventDefault();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      // focus next/prev card in current column
      const colItems = items.filter((i) => i.column === focusCol);
      const activeEl = document.activeElement as HTMLElement | null;
      const idx = colItems.findIndex((it) => activeEl?.dataset.itemId === it.id);
      if (idx >= 0) {
        const delta = e.key === 'ArrowDown' ? 1 : -1;
        const next = colItems[(idx + delta + colItems.length) % colItems.length];
        if (next) {
          const el = gridRef.current?.querySelector<HTMLElement>(`[data-item-id="${next.id}"]`);
          el?.focus();
          e.preventDefault();
        }
      }
    } else if (e.key === ' ' || e.key === 'Enter') {
      // pick up / drop with Space
      if (dragId) {
        onDrop(dragId, focusCol!);
        setDragId(null);
      }
      e.preventDefault();
    }
  };

  return (
    <div
      className="kanban"
      role="grid"
      aria-label="Kanban board"
      ref={gridRef}
      onKeyDown={handleGridKeyDown}
    >
      {columns.map((col) => {
        const colItems = items.filter((i) => i.column === col.id);
        const isOver = dragId !== null;
        return (
          <div
            key={col.id}
            className={`kanban-col${isOver ? ' kanban-col-over' : ''}${focusCol === col.id ? ' kanban-col-focus' : ''}`}
            role="row"
            aria-label={col.title}
            tabIndex={0}
            onFocus={() => setFocusCol(col.id)}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = 'move';
            }}
            onDrop={(e) => {
              e.preventDefault();
              const id = e.dataTransfer.getData('text/plain') || dragId;
              if (id) onDrop(id, col.id);
              setDragId(null);
            }}
          >
            <div className="kanban-col-head">
              <span className="kanban-col-title">{col.title}</span>
              <span className="kanban-col-count">{colItems.length}</span>
            </div>
            <div className="kanban-col-body" role="grid">
              {colItems.map((item) => (
                <div
                  key={item.id}
                  data-item-id={item.id}
                  className={`kanban-card${dragId === item.id ? ' kanban-card-drag' : ''}`}
                  role="gridcell"
                  tabIndex={0}
                  aria-label={`${col.title} item`}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', item.id);
                    e.dataTransfer.effectAllowed = 'move';
                    setDragId(item.id);
                  }}
                  onDragEnd={() => setDragId(null)}
                  onClick={onItemClick ? () => onItemClick(item) : undefined}
                >
                  {item.render(item)}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
