import { useEffect } from 'react';
import useFocusTrap from '../hooks/useFocusTrap';

interface DrawerProps {
  title?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
}

// Focus-trap note: drawer should trap focus like modal; basic loop added via onKeyDown.
export default function Drawer({ title, onClose, children, width = 560 }: DrawerProps) {
  const { containerRef: drawerRef, onKeyDown: handleKeyDown } = useFocusTrap();
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="overlay overlay-drawer" onClick={onClose} role="presentation" aria-label="Фоновое затемнение">
      <div
        ref={drawerRef}
        className="drawer"
        style={{ width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
      >
        <div className="drawer-head">
          <div id="drawer-title" className="drawer-title">{title}</div>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть" type="button">
            ✕
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  );
}