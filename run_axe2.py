import subprocess, time, urllib.request, os, sys, threading, http.server, socketserver

# Simple Python HTTP server in background
os.chdir('zarabotok/pipeline_v3/ui/dist')
handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(('127.0.0.1', 8091), handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
print('Server started on 8091, thread:', t.is_alive())
time.sleep(2)

try:
    r = urllib.request.urlopen('http://127.0.0.1:8091/', timeout=5)
    body = r.read()
    print('Server up, status:', r.status, 'size:', len(body))
except Exception as e:
    print('Server not up:', e)
    httpd.shutdown()
    sys.exit(1)

# Run axe-core
print('Running @axe-core/cli...')
result = subprocess.run(['npx.cmd', '-y', '@axe-core/cli', 'http://127.0.0.1:8091/', '--exit'], capture_output=True, text=True, timeout=180, shell=False)
print('axe exit:', result.returncode)
print('---STDOUT---')
print(result.stdout[:3000])
print('---STDERR---')
print(result.stderr[:2000])

with open('axe_result.log', 'w', encoding='utf-8') as f:
    f.write('EXIT: ' + str(result.returncode) + '\n\nSTDOUT:\n' + result.stdout + '\n\nSTDERR:\n' + result.stderr)

httpd.shutdown()
print('Server stopped, saved axe_result.log')
