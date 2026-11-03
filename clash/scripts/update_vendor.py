"""Explicit upstream snapshot refresh. Never commits, pushes, or touches subscriptions.
Run with reviewed 40-character commits, then render, test and inspect git diff.
"""
import argparse, hashlib, ipaddress, json, re, shutil, subprocess, tempfile
from pathlib import Path
from config import ROOT, verify_manifest

SOURCES = {'domain-list-community': 'https://github.com/v2fly/domain-list-community',
           'china-operator-ip': 'https://github.com/gaoyifan/china-operator-ip'}

def checkout(repository, revision, destination):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Supply an immutable full 40-character commit SHA, not a branch or tag')
    subprocess.run(['git', 'init', '-q', str(destination)], check=True)
    subprocess.run(['git', '-C', str(destination), 'remote', 'add', 'origin', repository+'.git'], check=True)
    subprocess.run(['git', '-C', str(destination), 'fetch', '--depth=1', 'origin', revision], check=True)
    subprocess.run(['git', '-C', str(destination), 'checkout', '-q', '--detach', 'FETCH_HEAD'], check=True)
    actual = subprocess.check_output(['git', '-C', str(destination), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision: raise ValueError('Upstream revision mismatch')

def file_bytes(root, relative):
    source = root/relative
    if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Unsafe upstream path: {relative}')
    return source.read_bytes()

def update(domain_revision, ip_revision):
    old = verify_manifest()
    revisions = {'domain-list-community': domain_revision, 'china-operator-ip': ip_revision}
    with tempfile.TemporaryDirectory(prefix='clash-vendor-') as tmp:
        tmp=Path(tmp); stage=tmp/'stage'; stage.mkdir()
        checkouts = {}
        for name, url in SOURCES.items():
            checkouts[name]=tmp/name
            checkout(url, revisions[name], checkouts[name])
        manifest = {'schema_version': 1, 'path_base': 'clash/vendor',
            'sources': [{'repository': url, 'revision': revisions[name], 'license': 'MIT'} for name,url in SOURCES.items()],
            'roots': old['roots'], 'files': [], 'licenses': []}
        def save(name, relative, category=None, fmt=None):
            data=file_bytes(checkouts[name], relative)
            target=stage/name/relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            item={'path': f'{name}/{relative}', 'url': f'{SOURCES[name].replace("https://github.com/", "https://raw.githubusercontent.com/")}/{revisions[name]}/{relative}',
                  'revision': revisions[name], 'sha256': hashlib.sha256(data).hexdigest(), 'license':'MIT'}
            if category is not None: item.update(category=category, format=fmt)
            return item
        # Changed licenses need deliberate review, not automatic reacceptance.
        for name in SOURCES:
            item=save(name, 'LICENSE')
            expected=next(x for x in old['licenses'] if x['path']==item['path'])
            if item['sha256'] != expected['sha256']:
                raise ValueError(f'{name} license changed; review license before updating the lock manifest')
            manifest['licenses'].append(item)
        names=set()
        def visit(name):
            if not re.fullmatch(r'[a-z0-9][a-z0-9!._-]*', name) or '..' in name:
                raise ValueError(f'Unsafe include: {name}')
            if name in names: return
            names.add(name)
            for line in file_bytes(checkouts['domain-list-community'], 'data/'+name).decode().splitlines():
                words=line.split('#',1)[0].split()
                if words and words[0].startswith('include:'): visit(words[0][8:])
        for paths in old['roots'].values():
            for path in paths:
                if path.startswith('domain-list-community/data/'): visit(path.rsplit('/',1)[1])
        visit('tencent') # provenance for owned WeChat rules, not a broad routing root
        for name in sorted(names):
            relative='data/'+name; path='domain-list-community/'+relative
            category=next((key for key, paths in old['roots'].items() if path in paths), '_dependency')
            manifest['files'].append(save('domain-list-community', relative, category, 'v2fly-domain-list'))
        for relative in ('china.txt', 'china6.txt'):
            for row in file_bytes(checkouts['china-operator-ip'], relative).decode().splitlines():
                if row.strip(): ipaddress.ip_network(row.strip(), strict=True)
            manifest['files'].append(save('china-operator-ip', relative, 'ChinaIP', 'cidr-lines'))
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        # Everything has been fetched and validated before tracked data is replaced.
        for name in SOURCES:
            target=ROOT/'vendor'/name
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(stage/name, target)
        shutil.copyfile(stage/'manifest.json', ROOT/'vendor/manifest.json')
        verify_manifest()
    print('Updated local snapshot only. Render, test, review git diff, then commit explicitly.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--domain-revision', required=True)
    parser.add_argument('--ip-revision', required=True)
    args=parser.parse_args(); update(args.domain_revision, args.ip_revision)
