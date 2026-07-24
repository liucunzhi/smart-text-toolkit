"""
Local Server Runner - Keep API running persistently
Usage: python run_local.py [--port 8000] [--host 0.0.0.0]
"""
import argparse
import subprocess
import sys
import time
import os

def main():
    parser = argparse.ArgumentParser(description='Smart Text Toolkit Local Server')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argumen
...[Truncated]...
tcp = f"http://{host}:{port}"
    cmd = [sys.executable, '-m', 'uvicorn', 'main:app', '--host', host, '--port', str(port)]

    print(f"Smart Text Toolkit API")
    print(f"Local:    http://127.0.0.1:{port}")
    print(f"Network:  http://{host}:{port}")
    print(f"Health:   http://127.0.0.1:{port}/api/health")
    print(f"Docs:     http://127.0.0.1:{port}/docs")
    print("-" * 50)

    while True:
        print(f"[{time.strftime('%H:%M:%S')}] Starting server...")
        proc = subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        proc.wait()
        print(f"[{time.strftime('%H:%M:%S')}] Server stopped. Restarting in 3s...")
        time.sleep(3)

if __name__ == '__main__':
    main()
