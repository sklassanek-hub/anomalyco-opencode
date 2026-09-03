import urllib.request
import json

token = 'TNh8mZGJUAHJGqLIMYdpJ99GzhJOr8'

endpoints = [
    '/api/projects/0.1/projects/active?limit=5&compact=true&job_details=true',
    '/api/projects/0.1/projects/active?limit=5&compact=true&job_details=true&query=python',
    '/api/projects/0.1/projects/active?limit=5&compact=true&job_details=true&min_budget=100&max_budget=5000',
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
            for p in projects[:2]:
                title = p.get('title', '')
                pid = p.get('id', '')
                budget = p.get('budget', {})
                print(f'    - {title} | {pid} | budget: {budget}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(e.code, ':', ep, '->', body)
    except Exception as e:
        print('ERR:', ep, '->', e)