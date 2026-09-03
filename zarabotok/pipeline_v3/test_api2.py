import urllib.request
import json

token = 'TNh8mZGJUAHJGqLIMYdpJ99GzhJOr8'

# Test project details
ep = '/api/projects/0.1/projects/40674979?full_description=true'
url = 'https://www.freelancer.com' + ep
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('OK:', ep, '->', r.status)
        data = json.loads(r.read().decode())
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(e.code, ':', ep, '->', body)
except Exception as e:
    print('ERR:', ep, '->', e)