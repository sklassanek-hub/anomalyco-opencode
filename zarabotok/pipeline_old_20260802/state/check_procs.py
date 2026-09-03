import subprocess
result = subprocess.run(
    ["wmic", "process", "where", 'name="python.exe"', "get", "ProcessId,CommandLine,ExecutablePath", "/format:list"],
    capture_output=True, text=True
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
