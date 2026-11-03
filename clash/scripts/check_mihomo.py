"""Offline parser check with fake file-backed subscriptions. No proxy process starts."""
import argparse, copy, json, subprocess, tempfile
from pathlib import Path
import config

def check(binary):
    with tempfile.TemporaryDirectory(prefix='clash-check-') as tmp:
        root = Path(tmp)
        profile, _ = config.build('flclash')
        for i, name in enumerate(profile['proxy-providers']):
            provider_path = root / f'provider-{i}.yaml'
            provider_path.write_text(config.dump({'proxies': [
                {'name': f'{region} synthetic {i}', 'type': 'http', 'server': '127.0.0.1', 'port': 9}
                for region in ('SG', 'JP', 'TW', 'US', 'HK')]}))
            profile['proxy-providers'][name] = {'type': 'file', 'path': str(provider_path)}
        target = root/'config.yaml'; target.write_text(config.dump(profile))
        subprocess.run([binary, '-t', '-d', str(root), '-f', str(target)], check=True, timeout=30)
        # All empty providers retain REJECT members; no silent DIRECT fallback.
        for i in range(len(profile['proxy-providers'])):
            (root / f'provider-{i}.yaml').write_text('proxies: []\n')
        subprocess.run([binary, '-t', '-d', str(root), '-f', str(target)], check=True, timeout=30)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('binary'); args = p.parse_args(); check(args.binary)
