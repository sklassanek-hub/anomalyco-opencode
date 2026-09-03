export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
  title?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T, index: number) => string;
  onRowClick?: (row: T) => void;
  emptyText?: string;
  loading?: boolean;
  dense?: boolean;
}

export default function Table<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  emptyText = 'Нет данных',
  loading = false,
  dense = false,
}: TableProps<T>) {
  return (
    <div className={`table-wrap${dense ? ' table-dense' : ''}`}>
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.className} title={c.title}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody onKeyDown={(e) => {
          if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
          const tbody = (e.currentTarget as HTMLElement);
          const rows = Array.from(tbody.querySelectorAll('tr.table-row-click')) as HTMLElement[];
          if (rows.length === 0) return;
          const active = document.activeElement as HTMLElement;
          const currentRow = active?.closest('tr.table-row-click') as HTMLElement | null;
          if (!currentRow) return;
          const idx = rows.indexOf(currentRow);
          if (idx === -1) return;
          const nextIdx = e.key === 'ArrowDown' ? idx + 1 : idx - 1;
          if (nextIdx >= 0 && nextIdx < rows.length) {
            e.preventDefault();
            rows[nextIdx].focus();
          }
        }}>
          {loading && (
            <tr>
              <td colSpan={columns.length} className="table-empty">
                <span className="spinner" /> Загрузка…
              </td>
            </tr>
          )}
          {!loading && data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="table-empty">
                {emptyText}
              </td>
            </tr>
          )}
          {!loading &&
            data.map((row, idx) => (
              <tr
                key={rowKey(row, idx)}
                className={onRowClick ? 'table-row-click' : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                role={onRowClick ? 'button' : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                aria-label={onRowClick ? `Выбрать строку: ${String((row as Record<string, unknown>)[columns[0]?.key] ?? '')}` : undefined}
                onKeyDown={onRowClick ? (e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onRowClick(row);
                  }
                } : undefined}
              >
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}