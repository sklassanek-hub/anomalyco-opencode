# needs_linking cleanup helper (P1 [ ])
# Clears stale 'needs_linking' flags in messages/order linkage state.
import os, json, time

def cleanup_needs_linking(state_path='zarabotok/pipeline_v3/state'):
    cleared = 0
    for fn in os.listdir(state_path):
        if not fn.endswith('.json'):
            continue
        path = os.path.join(state_path, fn)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, dict):
            msgs = data.get('messages', [])
            if isinstance(msgs, list):
                for m in msgs:
                    if isinstance(m, dict) and m.get('needs_linking'):
                        m['needs_linking'] = False
                        m['linked_at'] = time.time()
                        cleared += 1
            elif data.get('needs_linking'):
                data['needs_linking'] = False
                data['linked_at'] = time.time()
                cleared += 1
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'needs_linking cleanup: {cleared} flags cleared')

if __name__ == '__main__':
    cleanup_needs_linking()
