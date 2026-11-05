"""Small deterministic compiler for the two client profiles (no network IO)."""
from __future__ import annotations
import argparse, copy, hashlib, ipaddress, itertools, json, re, urllib.parse
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

class UniqueLoader(yaml.SafeLoader):
    pass

def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)

def load(path):
    return yaml.load(Path(path).read_text(), Loader=UniqueLoader)

def dump(data):
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)

def unique(items):
    return list(dict.fromkeys(items))

def domain_entries(path, stack=()):
    """Resolve includes before applying include attribute filters (v2fly semantics)."""
    path = Path(path)
    if path in stack:
        raise ValueError(f'cyclic include: {path}')
    entries = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        words = raw.split('#', 1)[0].split()
        if not words:
            continue
        token, attrs = words[0], {x[1:] for x in words[1:] if x.startswith('@')}
        if token.startswith('include:'):
            name = token.split(':', 1)[1]
            if '/' in name or name in {'.', '..'}:
                raise ValueError('unsafe include')
            included = domain_entries(path.parent / name, stack + (path,))
            for attr in attrs:
                included = [x for x in included if ((attr[1:] not in x[1]) if attr.startswith('-') else (attr in x[1]))]
            entries.extend(included)
        else:
            entries.append((token, attrs, path, number, raw.strip()))
    return entries

def expand_domains(path, selected_attr=None, stack=(), skipped=None):
    rules = []
    for token, attrs, origin, number, raw in domain_entries(path):
        if selected_attr and selected_attr not in attrs:
            continue
        kind, value = token.split(':', 1) if ':' in token else ('domain', token)
        modes = {'domain': 'DOMAIN-SUFFIX', 'full': 'DOMAIN', 'keyword': 'DOMAIN-KEYWORD'}
        if kind not in modes:
            if skipped is not None:
                skipped.append({'path': str(origin.relative_to(ROOT)), 'line': number, 'rule': raw, 'reason': 'outside shared domain/IP subset'})
            continue
        if not value or ',' in value:
            raise ValueError(f'invalid domain entry {origin}:{number}')
        rules.append(f'{modes[kind]},{value.lower()}')
    return unique(rules)

def add_target(rule, target):
    parts = rule.split(',')
    if len(parts) != 2 or parts[0] not in {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'IP-CIDR', 'IP-CIDR6'}:
        raise ValueError(f'unsupported shared rule: {rule}')
    if parts[0].startswith('IP-'):
        net = ipaddress.ip_network(parts[1], strict=True)
        if net.version != (6 if parts[0] == 'IP-CIDR6' else 4):
            raise ValueError(f'IP version mismatch: {rule}')
        return f'{rule},{target},no-resolve'
    return f'{rule},{target}'

def build_rules():
    policy = load(ROOT / 'shared/routing.yaml')
    local = load(ROOT / 'shared/rules/local.yaml')
    manifest = json.loads((ROOT / 'vendor/manifest.json').read_text())
    skipped, ordered, seen = [], [], set()
    categories = manifest['roots']
    file_types = {x['path']: x['format'] for x in manifest['files']}
    for section in policy['order']:
        target = section['target']
        rows = []
        if 'local' in section:
            rows = local[section['local']]
        elif 'owned' in section:
            rows = load(ROOT / 'shared/rules/services.yaml')[section['owned']]
        else:
            category = categories[section['category']]
            for source in category:
                path = ROOT / 'vendor' / source
                if file_types[source] == 'v2fly-domain-list':
                    rows += expand_domains(path, skipped=skipped)
                elif file_types[source] == 'cidr-lines':
                    for line in path.read_text().splitlines():
                        line = line.split('#', 1)[0].strip()
                        if line:
                            net = ipaddress.ip_network(line, strict=True)
                            rows.append(f'IP-CIDR{6 if net.version == 6 else ""},{net}')
                else:
                    raise ValueError(f'unsupported source format: {source}')
        for row in rows:
            # Exact duplicate predicates have first-match semantics, never duplicate targets.
            if row not in seen:
                ordered.append(add_target(row, target))
                seen.add(row)
    ordered.append('MATCH,兜底分流')
    return ordered, skipped

def groups(client, providers):
    spec = load(ROOT / 'shared/groups.yaml')
    auto = spec['automatic']
    result = [{'name': '直连', 'type': 'select', 'proxies': ['DIRECT']},
              {'name': '全球加速', 'type': 'select', 'proxies': spec['global_options']}]
    # Region groups contain only actual provider nodes matching that region.
    for region in spec['regions']:
        group = {'name': region['name'], 'type': 'url-test', 'proxies': [],
                 'use': list(providers), 'filter': region['filter'],
                 'interval': auto['interval'], 'tolerance': auto['tolerance'], 'lazy': auto['lazy']}
        group['url' if client == 'flclash' else 'benchmark-url'] = auto['url']
        result.append(group)
    # Keep REJECT in the catch-all health-tested group and manual selection as a guard.
    region = {'name': '自动选择', 'filter': '.*'}
    group = {'name': region['name'], 'type': 'url-test', 'proxies': ['REJECT'],
             'use': list(providers), 'filter': f'(?i)(?:.*)|^REJECT$',
             'interval': auto['interval'], 'tolerance': auto['tolerance'], 'lazy': auto['lazy']}
    group['url' if client == 'flclash' else 'benchmark-url'] = auto['url']
    result.append(group)
    result.append({'name': '手动选择', 'type': 'select', 'proxies': ['REJECT'], 'use': list(providers)})
    for item in spec['services']:
        choices = spec['service_options']
        choices = [item['default']] + [x for x in choices if x != item['default']]
        result.append({'name': item['name'], 'type': 'select', 'proxies': choices})
    return result

def dns_policy(rules, client):
    """Generate focused overseas DNS categories; other domains use domestic DNS."""
    foreign_targets = {'加密货币', 'AI 服务', 'GitHub', 'YouTube', 'Telegram', 'Google'}
    foreign = ['https://1.1.1.1/dns-query' + ('#自动选择' if client == 'flclash' else '')]
    policy = {}
    for row in rules:
        parts = row.split(',')
        if parts[0] in ('DOMAIN', 'DOMAIN-SUFFIX') and parts[2] in foreign_targets:
            key = ('+.' if parts[0] == 'DOMAIN-SUFFIX' else '') + parts[1]
            policy.setdefault(key, foreign)
    return policy

def provider_payloads(rules, client):
    """Create content-addressed reviewed files and compact provider references."""
    docs, entries, references = {}, {}, []
    root_url = 'https://raw.githubusercontent.com/bghtyu/dotfiles/main/clash/rules/sha256/'
    def register(name, behavior, payload, label):
        text = dump({'payload': payload})
        digest = hashlib.sha256(text.encode()).hexdigest()
        filename = f'{label}-{behavior}-{digest}.yaml'
        docs[filename] = text
        entry = {'behavior': behavior, 'format': 'yaml', 'url': root_url + filename, 'interval': 86400}
        if client == 'flclash':
            entry.update({'type': 'http', 'path': f'./rules/{name}-{digest}.yaml'})
        entries[name] = entry
    def kind(row):
        parts = row.split(',')
        return (parts[2], 'ipcidr' if parts[0].startswith('IP-') else 'domain')
    rows = [r for r in rules if not r.startswith('MATCH,')]
    name_counts = {}
    for (target, behavior), chunk in itertools.groupby(rows, key=kind):
        chunk = list(chunk)
        payload = []
        for row in chunk:
            part = row.split(',')
            payload.append(('+' + '.' if part[0] == 'DOMAIN-SUFFIX' else '') + part[1])
        labels = {'直连': 'direct', '全球加速': 'global', '微信': 'wechat', '哔哩哔哩': 'bilibili',
                  '加密货币': 'crypto', 'AI 服务': 'ai', 'GitHub': 'github', 'YouTube': 'youtube',
                  'Telegram': 'telegram', '声田音乐': 'spotify', 'Google': 'google', '苹果服务': 'apple',
                  'Microsoft': 'microsoft', '国际媒体': 'media', '游戏服务': 'games', '国内服务': 'china'}
        label = labels.get(target)
        if label is None:
            raise ValueError(f'no stable provider label for routing target: {target}')
        base = f'{label}-{behavior}'
        name_counts[base] = name_counts.get(base, 0) + 1
        name = base if name_counts[base] == 1 else f'{base}-{name_counts[base]}'
        register(name, behavior, payload, label)
        references.append(f'RULE-SET,{name},{target}' + (',no-resolve' if behavior == 'ipcidr' else ''))
    policy = dns_policy(rules, client)
    register('proxy-dns', 'domain', list(policy), 'proxy-dns')
    return docs, entries, references

def build(client, subscription_file=None):
    result = load(ROOT / f'templates/{client}.yaml')
    subscriptions = load(subscription_file or ROOT / 'shared/subscriptions.example.yaml')['providers']
    auto = load(ROOT / 'shared/groups.yaml')['automatic']
    providers = {}
    for index, (name, item) in enumerate(subscriptions.items(), 1):
        if not isinstance(item.get('url'), str) or not item['url'].startswith('https://'):
            raise ValueError(f'HTTPS subscription URL required: {name}')
        provider = copy.deepcopy(item)
        if client == 'flclash':
            provider.update({'type': 'http', 'path': f'./proxy-providers/provider-{index}.yaml',
                'health-check': {'enable': True, 'url': auto['url'], 'interval': auto['interval'], 'lazy': auto['lazy']}})
        providers[name] = provider
    result['proxy-providers'] = providers
    result['proxy-groups'] = groups(client, providers)
    all_rules, skipped = build_rules()
    _, result['rule-providers'], references = provider_payloads(all_rules, client)
    result['rules'] = ['DOMAIN,dns.alidns.com,直连', 'DOMAIN,doh.pub,直连',
                       'IP-CIDR,1.1.1.1/32,自动选择,no-resolve'] + references + ['MATCH,兜底分流']
    foreign = 'https://1.1.1.1/dns-query' + ('#自动选择' if client == 'flclash' else '')
    domestic = ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query']
    result['dns']['nameserver'] = domestic
    result['dns']['proxy-server-nameserver'] = domestic
    if client == 'stash': result['dns']['follow-rule'] = True
    result['dns']['nameserver-policy'] = {'rule-set:proxy-dns': [foreign],
        'dns.alidns.com': domestic, 'doh.pub': domestic,
        # Bootstrap provider downloads before DNS proxy/route rules are ready.
        'raw.githubusercontent.com': domestic}
    for provider in providers.values():
        host = urllib.parse.urlsplit(provider['url']).hostname
        if host:
            result['dns']['nameserver-policy'][host] = domestic
    private = ['+.local', '+.lan', '+.localhost', '+.10.in-addr.arpa', '+.168.192.in-addr.arpa', '+.254.169.in-addr.arpa']
    private += [f'+.{part}.172.in-addr.arpa' for part in range(16, 32)]
    result['dns']['nameserver-policy'].update({key: ['system'] for key in private})
    return result, skipped

def verify_manifest():
    manifest = json.loads((ROOT / 'vendor/manifest.json').read_text())
    for item in manifest['files'] + manifest['licenses']:
        path = ROOT / 'vendor' / item['path']
        if not path.resolve().is_relative_to((ROOT / 'vendor').resolve()):
            raise ValueError('vendor path escape')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'vendor checksum mismatch: {path}')
    return manifest

def render(check=False, subscription_file=None, output_dir=None):
    verify_manifest()
    if subscription_file and not output_dir:
        raise ValueError('private subscriptions require --output-dir (never overwrite tracked examples)')
    output = Path(output_dir) if output_dir else ROOT
    if subscription_file and not output.resolve().is_relative_to((ROOT / 'local').resolve()):
        raise ValueError('private output must be under ignored clash/local/')
    output.mkdir(parents=True, exist_ok=True)
    rule_rows, _ = build_rules()
    documents, _, _ = provider_payloads(rule_rows, 'flclash')
    rule_dir = ROOT / 'rules' / 'sha256'
    if not check:
        rule_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in documents.items():
        digest = hashlib.sha256(data.encode()).hexdigest()
        if not filename.endswith(digest + '.yaml'): raise ValueError('rule filename/hash mismatch')
        file = rule_dir / filename
        if file.exists() and file.read_text() != data:
            raise ValueError(f'refusing to overwrite immutable rule file: {file}')
        if not file.exists():
            if check: raise ValueError(f'missing generated rule file: {file}')
            file.write_text(data)
    for client in ('flclash', 'stash'):
        config, skipped = build(client, subscription_file)
        text = '# Generated by scripts/config.py; edit shared/ and templates/, then render.\n'
        text += '# Example subscriptions are intentionally invalid; replace locally before use.\n'
        for license_item in verify_manifest()['licenses']:
            text += '# Source: ' + license_item['url'] + '\n'
            text += ''.join(('# ' + line).rstrip() + '\n' for line in (ROOT / 'vendor' / license_item['path']).read_text().splitlines())
        text += dump(config)
        path = output / f'{client}.yaml'
        if check:
            if not path.exists() or path.read_text() != text:
                raise ValueError(f'generated file is stale: {path}')
        else:
            path.write_text(text)
    report = json.dumps(unique([json.dumps(x, sort_keys=True) for x in skipped]), ensure_ascii=False, indent=2) + '\n'
    # Human-readable excluded upstream entries, also deterministically reviewed.
    report = json.dumps([json.loads(x) for x in json.loads(report)], ensure_ascii=False, indent=2) + '\n'
    path = output / 'excluded-rules.json'
    if check:
        if not path.exists() or path.read_text() != report:
            raise ValueError('exclusion report is stale')
    else:
        path.write_text(report)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--subscriptions', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    render(args.check, args.subscriptions, args.output_dir)
