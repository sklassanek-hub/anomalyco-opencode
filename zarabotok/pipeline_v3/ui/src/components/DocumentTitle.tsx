import { useEffect } from 'react';

export default function DocumentTitle({ title }: { title: string }) {
  useEffect(() => {
    document.title = title + ' — Zarabotok';
  }, [title]);
  return null;
}
