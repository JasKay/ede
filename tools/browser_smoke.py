"""Optional browser smoke test using installed Node/Playwright; never writes to live data."""
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = os.getenv("EDE_NODE") or shutil.which("node")
    if not node:
        raise RuntimeError("Install Node or set EDE_NODE for optional browser verification.")
    if not (ROOT / "data" / "ede_word_sense.json").exists():
        raise RuntimeError("Run tools/bootstrap_data.py before the real-corpus browser test.")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="ede-browser-") as directory:
        token = secrets.token_urlsafe(32)
        env = dict(os.environ, EDE_DB_PATH=str(Path(directory) / "test.db"),
                   EDE_DATA_DIR=str(ROOT / "data"), EDE_REVIEW_TOKEN=token)
        env.pop("SPACE_ID", None)
        base = f"http://127.0.0.1:{port}"
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError("Local API exited before startup")
                    try:
                        with urllib.request.urlopen(base + "/health", timeout=1) as response:
                            if json.load(response)["status"] == "ready":
                                break
                    except (OSError, ValueError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Local API startup timed out")
                result = subprocess.run(
                    [node, str(ROOT / "tests" / "browser-smoke.cjs")],
                    cwd=ROOT, env=env, input=json.dumps({"base": base, "token": token}),
                    text=True, encoding="utf-8", capture_output=True, timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                print(result.stdout.strip())
                if result.returncode:
                    raise RuntimeError(result.stderr.strip())
            except Exception:
                log.seek(0)
                # Server request logs do not include Authorization header values.
                print(log.read(), file=sys.stderr)
                raise
            finally:
                if os.name == "nt" and server.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(server.pid), "/T", "/F"],
                                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()
