export interface TabDef {
  id: string;
  label: string;
  count?: number;
}

interface TabsProps {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
}

export default function Tabs({ tabs, active, onChange }: TabsProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>, idx: number) => {
    let next = idx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      next = (idx + 1) % tabs.length;
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      next = (idx - 1 + tabs.length) % tabs.length;
    } else if (e.key === 'Home') {
      next = 0;
    } else if (e.key === 'End') {
      next = tabs.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    onChange(tabs[next].id);
    const parent = e.currentTarget;
    const buttons = parent.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    buttons[next]?.focus();
  };
  return (
    <div className="tabs" role="tablist" onKeyDown={(e) => {
      const idx = tabs.findIndex((t) => t.id === active);
      if (idx >= 0) handleKeyDown(e, idx);
    }}>
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={active === t.id}
          tabIndex={active === t.id ? 0 : -1}
          className={`tab${active === t.id ? ' tab-active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {typeof t.count === 'number' && <span className="tab-count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}