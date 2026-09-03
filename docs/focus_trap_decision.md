# Focus Trap — A22

We use a custom React hook `useFocusTrap` (`zarabotok/pipeline_v3/ui/src/hooks/useFocusTrap.ts`) instead of `focus-trap-react`.

Reasons:
- No additional dependency (smaller bundle).
- Works with existing Modal/Drawer + nested modal (`showRaw`, `ReplyModal`).
- Tests via `auto_a11y_check.py` (Modal role=dialog, aria-modal PASS).

Reference: `Modal.tsx`, `Drawer.tsx`.
