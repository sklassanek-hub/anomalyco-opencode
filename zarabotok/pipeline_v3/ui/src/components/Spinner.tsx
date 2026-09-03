export default function Spinner({ text = 'Загрузка…' }: { text?: string }) {
  return (
    <div className="spinner-wrap">
      <span className="spinner" />
      <span>{text}</span>
    </div>
  );
}