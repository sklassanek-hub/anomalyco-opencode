import { useEffect } from 'react';
import useFocusTrap from '../hooks/useFocusTrap';

interface ModalProps {
  title?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
}

// Focus-trap note: full trap requires JS loop (first/last focusable) and focus restoration.
// Added below via querySelectorAll loop on Tab/Shift+Tab; CSS overlay prevents background interaction.
export default function Modal({ title, onClose, children, footer, width = 640 }: ModalProps) {
  const { containerRef: modalRef, onKeyDown: handleKeyDown } = useFocusTrap();
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose} role="presentation" aria-label="Фоновое затемнение">
      <div
        ref={modalRef}
        className="modal"
        style={{ maxWidth: width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        onKeyDown={handleKeyDown}
      >
        <div className="modal-head">
          <div id="modal-title" className="modal-title">{title}</div>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть" type="button">
            ✕
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}