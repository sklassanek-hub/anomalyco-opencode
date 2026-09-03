import json
with open('.opencode/agents_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
ids = ['accessibility-auditor','agentic-search-optimizer','backend-architect','database-optimizer','mcp-builder','senior-project-manager','project-shepherd','software-architect','code-reviewer']
count = 0
for a in data.get('agents', []):
    if a.get('id') in ids:
        count += 1
        print(a['id'], 'kw=', len(a.get('keywords',[])), 'audit=', len(a.get('audit_refs',[])), 'ev=', len(a.get('evidence_links',[])), 'cross=', str(a.get('cross_reference_audit','NONE'))[:50])
print('Updated count:', count)
