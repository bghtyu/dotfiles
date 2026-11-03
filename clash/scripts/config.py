"""Small deterministic compiler for the two client profiles (no network IO)."""
from __future__ import annotations
import argparse, copy, hashlib, ipaddress, json, re
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
    # REJECT cannot complete a health check. It keeps missing/empty regions fail-closed,
    # instead of Stash's documented empty group => DIRECT behavior.
    for region in spec['regions'] + [{'name': '自动选择', 'filter': '.*'}]:
        group = {'name': region['name'], 'type': 'url-test', 'proxies': ['REJECT'],
                 'use': list(providers), 'filter': f'(?i)(?:{region["filter"].replace("(?i)", "")})|^REJECT$',
                 'interval': auto['interval'], 'tolerance': auto['tolerance'], 'lazy': auto['lazy']}
        group['url' if client == 'flclash' else 'benchmark-url'] = auto['url']
        result.append(group)
    result.append({'name': '手动选择', 'type': 'select', 'proxies': ['REJECT'], 'use': list(providers)})
    for item in spec['services']:
        choices = spec['service_options']
        choices = [item['default']] + [x for x in choices if x != item['default']]
        result.append({'name': item['name'], 'type': 'select', 'proxies': choices})
    return result

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
    result['rules'], skipped = build_rules()
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
