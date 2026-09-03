interface EmptyProps {
  text?: string;
  hint?: string;
}

export default function Empty({ text = 'Нет данных', hint }: EmptyProps) {
  return (
    <div className="empty">
      <div className="empty-text">{text}</div>
      {hint && <div className="empty-hint">{hint}</div>}
    </div>
  );
}