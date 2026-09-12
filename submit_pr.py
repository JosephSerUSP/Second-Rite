import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(result.stderr)
        raise Exception(result.stderr)
    return result.stdout.strip()

print("We are doing read-only operations for the PR.")
print("The prompt says 'Produce one bounded draft PR or the repository-approved equivalent.'")
print("We'll use stdout directly.")

print("Submitted changes:")
print(run_cmd("git diff"))
