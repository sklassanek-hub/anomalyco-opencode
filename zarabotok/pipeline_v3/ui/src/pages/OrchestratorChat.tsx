import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

async function fetchStatus() {
  const res = await fetch('/api/orchestrator/status');
  return res.json();
}

async function fetchQueue() {
  const res = await fetch('/api/orchestrator/queue');
  return res.json();
}

async function sendCommand(cmd: string) {
  const res = await fetch('/api/orchestrator/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command: cmd }),
  });
  return res.json();
}

export default function OrchestratorChat() {
  const queryClient = useQueryClient();
  const [cmd, setCmd] = useState('status');

  const { data: statusData } = useQuery({ queryKey: ['orch_status'], queryFn: fetchStatus, refetchInterval: 5000 });
  const { data: queueData } = useQuery({ queryKey: ['orch_queue'], queryFn: fetchQueue, refetchInterval: 5000 });
  const mutation = useMutation({ mutationFn: sendCommand, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orch_status', 'orch_queue'] }) });

  const handleSend = () => {
    if (cmd.trim()) mutation.mutate(cmd.trim());
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>Оркестратор: чат и управление</h1>
      <section style={{ marginBottom: 24 }}>
        <h2>Статус</h2>
        <pre style={{ background: '#f4f4f4', padding: 12 }}>{JSON.stringify(statusData || {}, null, 2)}</pre>
      </section>
      <section style={{ marginBottom: 24 }}>
        <h2>Очередь</h2>
        <pre style={{ background: '#f4f4f4', padding: 12 }}>{JSON.stringify(queueData || {}, null, 2)}</pre>
      </section>
      <section>
        <h2>Команда</h2>
        <input value={cmd} onChange={e => setCmd(e.target.value)} placeholder="status / refresh / restart / queue / pause / resume" style={{ width: 320, padding: 8 }} />
        <button onClick={handleSend} style={{ marginLeft: 8, padding: '8px 16px' }}>Отправить</button>
        {mutation.data && <pre style={{ background: '#e8f5e9', padding: 12, marginTop: 8 }}>{JSON.stringify(mutation.data, null, 2)}</pre>}
      </section>
    </div>
  );
}
