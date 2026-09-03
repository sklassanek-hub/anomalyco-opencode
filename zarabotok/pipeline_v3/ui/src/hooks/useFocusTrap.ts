import { useEffect, useRef } from 'react';

export default function useFocusTrap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const prevFocusedRef = useRef<Element | null>(null);

  useEffect(() => {
    prevFocusedRef.current = document.activeElement;
    const timer = setTimeout(() => {
      const el = containerRef.current;
      if (!el) return;
      const focusable = el.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable.length > 0) {
        (focusable[0] as HTMLElement).focus();
      } else {
        el.focus();
      }
    }, 0);
    return () => {
      clearTimeout(timer);
      if (prevFocusedRef.current && 'focus' in (prevFocusedRef.current as HTMLElement)) {
        (prevFocusedRef.current as HTMLElement).focus();
      }
    };
  }, []);

  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'Tab') return;
    const el = containerRef.current;
    if (!el) return;
    const focusable = el.querySelectorAll('[tabindex]:not([tabindex="-1"])') as NodeListOf<HTMLElement>;
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return { containerRef, onKeyDown, prevFocusedRef };
}
