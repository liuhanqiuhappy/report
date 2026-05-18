import subprocess
import sys

print("Starting server...")
print(f"Python path: {sys.executable}")

result = subprocess.run(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
    capture_output=True,
    text=True,
    timeout=30
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)