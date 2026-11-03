import hashlib, importlib.util, ipaddress, json, re, tempfile, unittest
from pathlib import Path
SPEC = importlib.util.spec_from_file_location('config', Path(__file__).resolve().parents[1] / 'scripts/config.py')
c = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(c)

def route(config, host):
    host = host.lower().rstrip('.')
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    for row in config['rules']:
        fields = row.split(',')
        kind = fields[0]
        if kind == 'MATCH': return fields[1]
        if kind == 'RULE-SET':
            provider = config['rule-providers'][fields[1]]
            digest = provider['url'].rsplit('/', 1)[-1]
            payload = c.load(c.ROOT/'rules/sha256'/digest)['payload']
            if provider['behavior'] == 'domain':
                if any((host == v[2:] or host.endswith('.'+v[2:])) if v.startswith('+.') else host == v for v in payload): return fields[2]
            elif ip and any(ip in ipaddress.ip_network(v) for v in payload): return fields[2]
            continue
        value, target = fields[1:3]
        if kind == 'DOMAIN' and host == value: return target
        if kind == 'DOMAIN-SUFFIX' and (host == value or host.endswith('.' + value)): return target
        if kind == 'DOMAIN-KEYWORD' and value in host: return target
        if kind in ('IP-CIDR', 'IP-CIDR6') and ip and ip in ipaddress.ip_network(value): return target
    raise AssertionError('no MATCH')

class ConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = {client: c.build(client)[0] for client in ('flclash', 'stash')}

    def test_generation_and_hashes(self):
        c.verify_manifest(); c.render(check=True)

    def test_rule_file_content_addressing(self):
        files = list((c.ROOT/'rules/sha256').glob('*.yaml'))
        self.assertTrue(files)
        for file in files:
            expected = file.stem.rsplit('-', 1)[-1]
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), expected, str(file))
        for profile in self.profiles.values():
            for provider in profile['rule-providers'].values():
                filename = provider['url'].rsplit('/', 1)[-1]
                self.assertTrue((c.ROOT/'rules/sha256'/filename).exists())

    def test_identical_routes_and_group_semantics(self):
        a, b = self.profiles.values()
        self.assertEqual(a['rules'], b['rules'])
        for ga, gb in zip(a['proxy-groups'], b['proxy-groups']):
            aa, bb = dict(ga), dict(gb)
            aa.pop('url', None); bb.pop('benchmark-url', None)
            self.assertEqual(aa, bb)

    def test_group_references_cycles_and_defaults(self):
        spec = c.load(c.ROOT / 'shared/groups.yaml')
        for profile in self.profiles.values():
            groups = {g['name']: g for g in profile['proxy-groups']}
            self.assertEqual(len(groups), len(profile['proxy-groups']))
            self.assertEqual(groups['全球加速']['proxies'], spec['global_options'])
            for service in spec['services']:
                g = groups[service['name']]
                self.assertEqual(set(g['proxies']), set(spec['service_options']))
                self.assertEqual(g['proxies'][0], service['default'])
            def visit(name, stack=()):
                self.assertNotIn(name, stack)
                if name in ('DIRECT', 'REJECT'): return
                self.assertIn(name, groups)
                for child in groups[name].get('proxies', []): visit(child, stack + (name,))
            for name, group in groups.items():
                visit(name)
                for provider in group.get('use', []): self.assertIn(provider, profile['proxy-providers'])
            for row in profile['rules']:
                fields = row.split(',')
                self.assertIn(fields[1] if fields[0] == 'MATCH' else fields[2], groups)
                if fields[0] == 'RULE-SET': self.assertIn(fields[1], profile['rule-providers'])

    def test_region_filters_and_empty_fail_closed(self):
        samples = {'新加坡': ['SG 01', '新加坡 IPLC', '🇸🇬 Node'], '日本': ['JP 01', '日本 01'],
                   '台湾': ['TW 01', '台灣 01'], '美国': ['US 01', '🇺🇸 Node'], '香港': ['HK 01', '香港 01']}
        for profile in self.profiles.values():
            groups = {x['name']: x for x in profile['proxy-groups']}
            for region, names in samples.items():
                group = groups[region]
                self.assertEqual(group['type'], 'url-test')
                self.assertEqual(group['proxies'], ['REJECT'])
                self.assertNotIn('DIRECT', group['proxies'])
                # regex flags must be at start for Python and RE2 compatibility.
                pattern = group['filter']
                for name in names: self.assertTrue(re.search(pattern, name), (region, name))
                self.assertTrue(re.search(pattern, 'REJECT'))
                for other, other_names in samples.items():
                    if other != region:
                        for name in other_names: self.assertFalse(re.search(pattern, name), (region, name))

    def test_no_external_management_and_reviewed_rule_urls(self):
        for profile in self.profiles.values():
            for key in ('external-controller', 'external-controller-tls', 'external-ui', 'external-ui-url', 'http', 'geox-url'):
                self.assertNotIn(key, profile)
            self.assertFalse(profile.get('allow-lan', False))
            for row in profile['rules']:
                self.assertNotIn(row.split(',')[0], ['GEOIP', 'GEOSITE', 'IP-ASN', 'PROCESS-NAME'])
            for provider in profile['proxy-providers'].values():
                self.assertIn('.example.invalid/', provider['url'])
            for provider in profile['rule-providers'].values():
                self.assertTrue(provider['url'].startswith('https://raw.githubusercontent.com/bghtyu/dotfiles/main/clash/rules/sha256/'))

    def test_representative_services_and_overlap(self):
        samples = {'weixin.qq.com': '微信', 'servicewechat.com': '微信', 'www.bilibili.com': '哔哩哔哩',
            'api.binance.com': '加密货币', 'www.coinbase.com': '加密货币', 'github.com': 'GitHub',
            'api.github.com': 'GitHub', 'chatgpt.com': 'AI 服务', 'api.openai.com': 'AI 服务',
            'claude.ai': 'AI 服务', 'gemini.google.com': 'AI 服务', 'api.githubcopilot.com': 'AI 服务',
            'www.google.com': 'Google', 'www.youtube.com': 'YouTube', 'www.apple.com': '苹果服务',
            't.me': 'Telegram', 'www.spotify.com': '声田音乐', 'www.microsoft.com': 'Microsoft',
            'www.netflix.com': '国际媒体', 'store.steampowered.com': '游戏服务', 'www.baidu.com': '国内服务',
            'www.taobao.com': '国内服务', 'qq.com': '国内服务', '10.0.0.1': '直连', '::1': '直连',
            '223.5.5.5': '国内服务', 'unclassified.example': '兜底分流'}
        for profile in self.profiles.values():
            for host, target in samples.items(): self.assertEqual(route(profile, host), target, host)

    def test_dns_split_and_cycle_guards(self):
        for client, profile in self.profiles.items():
            dns = profile['dns']
            foreign = 'https://1.1.1.1/dns-query' + ('#自动选择' if client == 'flclash' else '')
            self.assertEqual(dns['nameserver'], ['https://dns.alidns.com/dns-query', 'https://doh.pub/dns-query'])
            provider = profile['rule-providers']['proxy-dns']
            payload = c.load(c.ROOT/'rules/sha256'/provider['url'].rsplit('/',1)[-1])['payload']
            self.assertIn('+.google.com', payload)
            self.assertNotIn('+.baidu.com', payload)
            self.assertEqual(dns['nameserver-policy']['+.local'], ['system'])
            self.assertIn('+.github.com', payload)
            self.assertNotIn('+.cn', payload)
            self.assertIn('+.google.cn', payload)
            self.assertNotIn('https://1.1.1.1/dns-query', dns['proxy-server-nameserver'])
            self.assertEqual(profile['rules'][:3], ['DOMAIN,dns.alidns.com,直连', 'DOMAIN,doh.pub,直连', 'IP-CIDR,1.1.1.1/32,自动选择,no-resolve'])
            if client == 'stash': self.assertTrue(dns['follow-rule'])
            else: self.assertEqual(next(x for x in profile['proxy-groups'] if x['name'] == '自动选择')['proxies'], ['REJECT'])

    def test_duplicate_yaml_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.yaml'; path.write_text('x: 1\nx: 2\n')
            with self.assertRaises(ValueError): c.load(path)

    def test_include_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'root').write_text('include:child @-!cn\n')
            (p/'child').write_text('a.cn @cn\nb.com @!cn\ninclude:grand\n')
            (p/'grand').write_text('c.cn @cn\nd.com @!cn\n')
            self.assertEqual(c.expand_domains(p/'root'), ['DOMAIN-SUFFIX,a.cn', 'DOMAIN-SUFFIX,c.cn'])

    def test_private_render_cannot_overwrite_examples(self):
        with self.assertRaises(ValueError): c.render(subscription_file=c.ROOT/'shared/subscriptions.example.yaml')
        with self.assertRaises(ValueError):
            c.render(subscription_file=c.ROOT/'shared/subscriptions.example.yaml', output_dir=c.ROOT/'shared')

if __name__ == '__main__': unittest.main()
