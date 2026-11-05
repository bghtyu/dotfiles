"""Check vendored Stash bytes, immutable references and reviewed loader surface offline.

This is an integrity/regression gate, not a JavaScript sandbox or a security audit.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path('clash/stash/scripts')
OVERRIDES = Path('clash/stash/overrides')
BLOCKED = {
    'https://raw.githubusercontent.com/ddgksf2013/Scripts/'
    '97b8abea5ff52b5874c90d106d241e99894460d1/weixin110.js'
}


def verify(root=ROOT):
    snapshot = json.loads((root / SCRIPTS / 'snapshot.json').read_text())
    sources = json.loads((root / OVERRIDES / 'sources.json').read_text())
    commit = sources['script_snapshot_commit']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Snapshot must name a full commit')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', commit, 'HEAD'],
                   capture_output=True, check=True)
    expected = {}
    for asset in snapshot['assets']:
        rel = SCRIPTS / asset['path']
        if rel.parent != SCRIPTS / 'sha256' or not rel.name.endswith('-' + asset['sha256'] + '.js'):
            raise ValueError(f'Invalid content-addressed path: {rel}')
        data = (root / rel).read_bytes()
        if len(data) != asset['bytes'] or hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError(f'Script bytes differ: {rel}')
        pinned = subprocess.run(['git', '-C', str(root), 'show', f'{commit}:{rel.as_posix()}'],
                                capture_output=True, check=True).stdout
        if pinned != data:
            raise ValueError(f'Local bytes differ from snapshot commit: {rel}')
        source = data.decode('utf-8')
        if re.search(r'\b(?:eval|Function)\s*\(|\bimport\s*(?:\(|["\'{*])', source):
            raise ValueError(f'Unreviewed dynamic execution/import: {rel}')
        requires = re.findall(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)', source)
        remaining = re.sub(r'\brequire\s*\(\s*["\'][^"\']+["\']\s*\)', '', source)
        if re.search(r'\brequire\s*\(', remaining) or set(requires) != set(asset['allowed_literal_requires']):
            raise ValueError(f'Unreviewed module loader: {rel}')
        # Env retains these unused method declarations, but the business has no calls.
        if re.search(r'\.\s*(?:getScript|runScript)\s*\(', source):
            raise ValueError(f'Unreviewed secondary script call: {rel}')
        if asset['runtime_script_dependencies']:
            raise ValueError(f'New runtime script dependencies need review: {rel}')
        subprocess.run(['node', '--check', str(root / rel)], capture_output=True, check=True)
        expected[rel.as_posix()] = asset
    actual = {p.relative_to(root).as_posix() for p in (root / SCRIPTS / 'sha256').glob('*.js')}
    if actual != set(expected):
        raise ValueError('Untracked or missing snapshot script')
    referenced, blocked = set(), set()
    for override in sources['overrides']:
        override_path = root / OVERRIDES / override['file']
        if hashlib.sha256(override_path.read_bytes()).hexdigest() != override['sha256']:
            raise ValueError(f'Override bytes differ: {override_path}')
        providers = yaml.safe_load(override_path.read_text())['script-providers']
        if {p['url'] for p in providers.values()} != {s['url'] for s in override['scripts']}:
            raise ValueError(f'Provider references differ: {override_path}')
        for script in override['scripts']:
            if script['vendoring_status'] == 'blocked-license':
                if script['url'] not in BLOCKED or 'vendored_path' in script or not script['blocker']:
                    raise ValueError('Unexpected external script exception')
                blocked.add(script['url'])
                continue
            path = script['vendored_path']
            asset = expected[path]
            url = f'https://raw.githubusercontent.com/bghtyu/dotfiles/{commit}/{path}'
            if script['url'] != url or script['sha256'] != asset['sha256'] or script['bytes'] != asset['bytes']:
                raise ValueError(f'Provider does not match snapshot: {path}')
            referenced.add(path)
    if referenced != set(expected) or blocked != BLOCKED:
        raise ValueError('Snapshot references or documented exceptions differ')
    return len(expected), len(blocked)


if __name__ == '__main__':
    count, blocked = verify()
    print(f'Verified {count} repository scripts; {blocked} explicit license-blocked external script')
