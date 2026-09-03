interface CardProps {
  title?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  onClick?: () => void;
  children: React.ReactNode;
  accent?: 'ok' | 'warn' | 'err' | 'info' | 'none' | 'blue' | 'gray';
}

export default function Card({ title, actions, className = '', onClick, children, accent }: CardProps) {
  return (
    <div
      className={`card${accent ? ` card-accent-${accent}` : ''}${onClick ? ' card-clickable' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      } : undefined}
      aria-label={onClick ? (typeof title === 'string' ? title : 'Карточка') : undefined}
    >
      {(title || actions) && (
        <div className="card-head">
          <div className="card-title">{title}</div>
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
}