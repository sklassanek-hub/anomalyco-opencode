import urllib.request
import json

token = 'TNh8mZGJUAHJGqLIMYdpJ99GzhJOr8'

# Test bid placement endpoint (just check if it exists)
# We won't actually place a bid, just check the endpoint
ep = '/api/projects/0.1/bids/'
url = 'https://www.freelancer.com' + ep
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('OK:', ep, '->', r.status)
        data = json.loads(r.read().decode())
        print(json.dumps(data, indent=2)[:1000])
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(e.code, ':', ep, '->', body)
except Exception as e:
    print('ERR:', ep, '->', e)

# Check project bid stats to understand bidding
ep = '/api/projects/0.1/projects/40674979/bids/'
url = 'https://www.freelancer.com' + ep
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('\nProject bids:')
        print('OK:', ep, '->', r.status)
        data = json.loads(r.read().decode())
        print(json.dumps(data, indent=2)[:2000])
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(e.code, ':', ep, '->', body)
except Exception as e:
    print('ERR:', ep, '->', e)