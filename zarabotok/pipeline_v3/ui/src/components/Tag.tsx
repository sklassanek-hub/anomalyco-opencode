import type { Tone } from '../lib/types';

interface TagProps {
  tone?: Tone;
  children: React.ReactNode;
}

export default function Tag({ tone = 'gray', children }: TagProps) {
  return <span className={`tag tag-${tone}`}>{children}</span>;
}