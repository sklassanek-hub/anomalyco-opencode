import subprocess, time, urllib.request, sys
proc = subprocess.Popen(['npx.cmd', '-y', 'http-server', '-p', '8090', '-s'], cwd='zarabotok/pipeline_v3/ui/dist', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('Started server PID:', proc.pid)
time.sleep(8)
try:
    r = urllib.request.urlopen('http://127.0.0.1:8090/', timeout=5)
    body = r.read()
    print('Server up, status:', r.status, 'size:', len(body))
except Exception as e:
    print('Server not up:', e)
    proc.terminate()
    sys.exit(1)

# Now run axe-core
result = subprocess.run(['npx.cmd', '-y', '@axe-core/cli', 'http://127.0.0.1:8090/', '--exit'], capture_output=True, text=True, timeout=120, shell=True)
print('axe exit:', result.returncode)
print('axe stdout:')
print(result.stdout)
print('axe stderr:')
print(result.stderr[:2000])

# Save to log
with open('axe_result.log', 'w', encoding='utf-8') as f:
    f.write('EXIT: ' + str(result.returncode) + '\n')
    f.write('STDOUT:\n' + result.stdout + '\n')
    f.write('STDERR:\n' + result.stderr + '\n')

proc.terminate()
print('Server stopped')
