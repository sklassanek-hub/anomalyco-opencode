import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

export type ToastType = 'ok' | 'err' | 'info' | 'warn';

interface Toast {
  id: number;
  type: ToastType;
  text: string;
}

interface ToastCtx {
  push: (type: ToastType, text: string) => void;
}

const Ctx = createContext<ToastCtx>({ push: () => {} });

export function useToast(): ToastCtx {
  return useContext(Ctx);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const push = useCallback((type: ToastType, text: string) => {
    const id = nextId.current++;
    setItems((prev) => [...prev, { id, type, text }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="toast-wrap" aria-live="polite" aria-atomic="true" role="status">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`} role="status" aria-label={t.text}>
            {t.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}