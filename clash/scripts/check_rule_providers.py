"""Offline loopback-only Mihomo HTTP rule-provider and cache characterization."""
import argparse, contextlib, http.server, json, socket, struct, subprocess, tempfile, threading, time, urllib.request
from pathlib import Path
import yaml

PAYLOADS = {
    '/domain.yaml': b'payload:\n  - "+.example.test"\n',
    '/ip.yaml': b'payload:\n  - "192.0.2.0/24"\n',
    '/classical.yaml': b'payload:\n  - "DOMAIN,exact.example.test"\n',
}
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in PAYLOADS:
            self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type', 'application/yaml'); self.end_headers(); self.wfile.write(PAYLOADS[self.path])
    def log_message(self,*args): pass

def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]

class MockDNS:
    def __init__(self, address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 0)); self.address = socket.inet_aton(address)
        threading.Thread(target=self.serve, daemon=True).start()
    @property
    def port(self): return self.sock.getsockname()[1]
    def serve(self):
        while True:
            try:
                request, peer = self.sock.recvfrom(4096)
                # One A record answer, preserving the original question.
                response = request[:2] + b'\x81\x80' + request[4:6] + b'\x00\x01\x00\x00\x00\x00' + request[12:] + b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + self.address
                self.sock.sendto(response, peer)
            except OSError: return

def dns_query(dns_port, domain):
    request = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    request += b''.join(bytes([len(x)]) + x.encode() for x in domain.split('.')) + b'\x00\x00\x01\x00\x01'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3); sock.sendto(request, ('127.0.0.1', dns_port)); result = sock.recv(4096)
    return socket.inet_ntoa(result[-4:])

def run(binary, directory, url_port, expect_success):
    api_port = port()
    dns_port = port()
    domestic, foreign = MockDNS('192.0.2.1'), MockDNS('198.51.100.1')
    providers = {name: {'type': 'http', 'behavior': behavior, 'format': 'yaml', 'url':f'http://127.0.0.1:{url_port}/{name}.yaml', 'path':f'./providers/{name}.yaml', 'interval':86400} for name, behavior in [('domain','domain'),('ip','ipcidr'),('classical','classical')]}
    profile = {'mixed-port': 0, 'allow-lan': False, 'external-controller':f'127.0.0.1:{api_port}', 'secret':'loopback-only', 'dns': {'enable':True, 'listen':f'127.0.0.1:{dns_port}', 'enhanced-mode':'redir-host', 'nameserver':[f'127.0.0.1:{foreign.port}'], 'nameserver-policy': {'rule-set:domain': [f'127.0.0.1:{domestic.port}']}}, 'rule-providers': providers, 'rules':['IP-CIDR,127.0.0.0/8,DIRECT,no-resolve','RULE-SET,classical,DIRECT','RULE-SET,domain,DIRECT','RULE-SET,ip,DIRECT,no-resolve','MATCH,REJECT']}
    config = directory/'config.yaml'; config.write_text(yaml.safe_dump(profile,sort_keys=False))
    with (directory/'run.log').open('w') as log:
        process = subprocess.Popen([binary,'-d',str(directory),'-f',str(config)],stdout=log,stderr=log)
        try:
            result = None
            for _ in range(100):
                if process.poll() is not None: break
                try:
                    req = urllib.request.Request(f'http://127.0.0.1:{api_port}/providers/rules',headers={'Authorization':'Bearer loopback-only'})
                    with urllib.request.urlopen(req,timeout=.5) as response: result=json.load(response)
                    if all((directory/'providers'/f'{name}.yaml').exists() for name in providers): break
                except (OSError, ValueError): pass
                time.sleep(.1)
            if expect_success:
                assert result is not None, (process.poll(),(directory/'run.log').read_text())
                assert all((directory/'providers'/f'{name}.yaml').exists() for name in providers), (result, (directory/'run.log').read_text())
                for name in providers:
                    assert (directory/'providers'/f'{name}.yaml').read_bytes() == PAYLOADS[f'/{name}.yaml']
            else:
                assert result is not None and process.poll() is None, (result, process.poll())
                assert all(result['providers'][name]['ruleCount'] == 0 for name in providers), result
                assert not any((directory/'providers'/f'{name}.yaml').exists() for name in providers)
            answer = dns_query(dns_port, 'www.example.test')
            assert answer == ('192.0.2.1' if expect_success else '198.51.100.1'), answer
            return {'core_api_ready':result is not None,'status': process.poll(), 'rule_counts': {name: result['providers'][name]['ruleCount'] for name in providers}, 'cached_files':sum((directory/'providers'/f'{name}.yaml').exists() for name in providers), 'matched_dns_answer':answer}
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill();process.wait()
            domestic.sock.close(); foreign.sock.close()

def main(binary):
    with tempfile.TemporaryDirectory(prefix='rule-provider-test-') as t:
        root = Path(t); cached = root/'cached'; cold = root/'cold'; cached.mkdir(); cold.mkdir()
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0), Handler); server_port = server.server_port
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try: first = run(binary,cached,server_port,True)
        finally: server.shutdown(); server.server_close()
        warm = run(binary,cached,server_port,True)
        missing = run(binary,cold,server_port,False)
        print(json.dumps({'first_fetch':first,'offline_cached':warm,'offline_cold':missing}))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('binary');main(p.parse_args().binary)
