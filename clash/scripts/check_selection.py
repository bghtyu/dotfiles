"""Loopback-only Mihomo selection characterization; no real subscriptions or internet.
The test-only controller binds 127.0.0.1, never appears in shipped profiles.
"""
import argparse, contextlib, http.server, json, socket, subprocess, tempfile, threading, time, urllib.parse, urllib.request
from pathlib import Path
import config

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); return sock.getsockname()[1]

class MockProxy(http.server.BaseHTTPRequestHandler):
    def do_CONNECT(self):
        self.send_response(200); self.end_headers()
        # Mimic an HTTP target inside CONNECT without dialing any destination.
        while True:
            line = self.rfile.readline()
            if not line or line in (b'\r\n', b'\n'): break
        time.sleep(0.01)
        self.wfile.write(b'HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n')
        self.wfile.flush()
        self.close_connection = True
    def do_GET(self):
        time.sleep(0.01)
        self.send_response(204); self.end_headers()
    def log_message(self, *args): pass

def check(binary):
    with tempfile.TemporaryDirectory(prefix='clash-select-') as tmp:
        root = Path(tmp)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), MockProxy)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for with_node in (True, False):
                api_port = free_port()
                profile, _ = config.build('flclash')
                # Use a local file fixture; PR rule URLs only exist on main after merge.
                for name, rule in profile['rule-providers'].items():
                    source = config.ROOT / 'rules/sha256' / rule['url'].rsplit('/', 1)[-1]
                    path = root / ('rule-' + name + '.yaml')
                    path.write_text(source.read_text())
                    rule.update({'type': 'file', 'path': str(path)})
                    rule.pop('url', None)
                profile.update({'mixed-port': 0, 'external-controller': f'127.0.0.1:{api_port}', 'secret': 'synthetic-local-test', 'dns': {'enable': False}})
                for i, name in enumerate(profile['proxy-providers']):
                    path = root / f'{i}.yaml'
                    nodes = [{'name': f'SG synthetic {i}', 'type': 'http', 'server': '127.0.0.1', 'port': server.server_port}] if with_node else []
                    path.write_text(config.dump({'proxies': nodes}))
                    profile['proxy-providers'][name] = {'type': 'file', 'path': str(path), 'health-check': {'enable': True, 'url': 'http://127.0.0.1/health', 'interval': 600, 'lazy': True}}
                for group in profile['proxy-groups']:
                    if group['type'] == 'url-test':
                        group['url'] = 'http://127.0.0.1/health'
                path = root/'config.yaml'; path.write_text(config.dump(profile))
                with (root/'run.log').open('w') as log:
                    proc = subprocess.Popen([binary, '-d', str(root), '-f', str(path)], stdout=log, stderr=log)
                    try:
                        result = None
                        for _ in range(100):
                            if proc.poll() is not None: raise RuntimeError((root/'run.log').read_text())
                            req = urllib.request.Request(f'http://127.0.0.1:{api_port}/proxies/'+urllib.parse.quote('新加坡'), headers={'Authorization': 'Bearer synthetic-local-test'})
                            try:
                                with urllib.request.urlopen(req, timeout=1) as response: result = json.load(response)
                                if (with_node and result['now'].startswith('SG synthetic')) or (not with_node and result['now'] == 'REJECT'): break
                            except (OSError, ValueError): pass
                            time.sleep(0.1)
                        assert result is not None, 'no proxy status'
                        expected = result['now'].startswith('SG synthetic') if with_node else result['now'] == 'REJECT'
                        assert expected, (result, (root/'run.log').read_text())
                        assert 'DIRECT' not in result['all'], result
                        print(json.dumps({'with_node': with_node, 'selected': result['now'], 'members': result['all']}, ensure_ascii=False))
                    finally:
                        proc.terminate()
                        try: proc.wait(timeout=5)
                        except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        finally:
            server.shutdown(); server.server_close()

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('binary'); a=p.parse_args(); check(a.binary)
