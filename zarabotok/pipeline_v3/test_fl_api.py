import urllib.request, json

token = '1YS6sxGUr7910m5amGUMQ4qqipr4S3'
base = 'https://www.freelancer.com/api'

endpoints = [
    '/projects/0.1/projects/active/?limit=5&compact=true&job_details=true',
    '/projects/0.1/projects/active/?limit=5&compact=true&job_details=true&skills[]=python',
    '/projects/0.1/projects/active/?limit=5&compact=true&job_details=true&min_budget=100&max_budget=5000',
    '/projects/0.1/projects/active/?limit=5&compact=true&job_details=true&query=web',
]

for ep in endpoints:
    url = base + ep
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            print(ep + ': ' + str(r.status))
            projects = data.get('result', {}).get('projects', [])
            print('  Projects: ' + str(len(projects)))
            for p in projects[:2]:
                print('    ' + p.get('title', '')[:60] + ' | ' + p.get('seo_url', '')[:50])
            print()
    except urllib.error.HTTPError as e:
        print(ep + ': ' + str(e.code))
        print(e.read().decode()[:200])
        print()
    except Exception as e:
        print(ep + ': ' + type(e).__name__ + ': ' + str(e))
        print()