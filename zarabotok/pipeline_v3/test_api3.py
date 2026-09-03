import urllib.request
import json

token = 'TNh8mZGJUAHJGqLIMYdpJ99GzhJOr8'

# Test skills filter
endpoints = [
    '/api/projects/0.1/projects/active?limit=5&compact=true&job_details=true&skills[]=python',
    '/api/projects/0.1/projects/active?limit=5&compact=true&job_details=true&skills[]=python&skills[]=django',
    '/api/projects/0.1/projects/active?limit=10&compact=true&job_details=true&project_types[]=fixed',
]

for ep in endpoints:
    url = 'https://www.freelancer.com' + ep
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print('OK:', ep, '->', r.status)
            data = json.loads(r.read().decode())
            projects = data.get('result', {}).get('projects', [])
            print(f'  Found {len(projects)} projects')
            for p in projects[:3]:
                title = p.get('title', '')
                pid = p.get('id', '')
                budget = p.get('budget', {})
                jobs = p.get('jobs', [])
                job_names = [j.get('name', '') for j in jobs]
                print(f'    - {title} | {pid} | budget: {budget} | skills: {job_names}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(e.code, ':', ep, '->', body)
    except Exception as e:
        print('ERR:', ep, '->', e)

# Test pagination
print('\n--- Pagination test ---')
for offset in [0, 5, 10]:
    ep = f'/api/projects/0.1/projects/active?limit=5&compact=true&offset={offset}'
    url = 'https://www.freelancer.com' + ep
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            projects = data.get('result', {}).get('projects', [])
            print(f'  Offset {offset}: {len(projects)} projects')
    except Exception as e:
        print(f'  Offset {offset}: ERR: {e}')