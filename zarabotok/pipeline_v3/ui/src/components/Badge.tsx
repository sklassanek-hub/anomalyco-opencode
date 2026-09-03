import type { Tone } from '../lib/types';

interface BadgeProps {
  tone?: Tone;
  children: React.ReactNode;
  title?: string;
}

export default function Badge({ tone = 'gray', children, title }: BadgeProps) {
  const label = title || (typeof children === 'string' ? children : undefined);
  return (
    <span className={`badge badge-${tone}`} title={title} aria-label={label} role="status">
      {children}
    </span>
  );
}