"""Offline regression checks for opt-in HTTPS scope and routing isolation.

This models documented Stash merge rules, not the native Stash parser/runtime.
"""
import copy
import hashlib
import itertools
import json
import re
import unittest
from test_config import c

DIRECTORY = c.ROOT / 'stash/overrides'
METADATA = {'name', 'desc', 'openUrl', 'author', 'homepage', 'icon', 'category', 'date', 'version'}
HOSTS = {
    'bilibili': {
        'biliverse.github.io', 'manga.bilibili.com', 'api.live.bilibili.com',
        'api.vc.bilibili.com', 'app.bilibili.com', 'app.biliapi.net',
        'app.biliapi.com', 'api.bilibili.com', 'api.biliapi.net',
        'grpc.biliapi.net', 'cm.bilibili.com', 'adtrack.qianwen.com',
        'tkio-redirect.solar-engine.com',
    },
    'wx110': {'weixin110.qq.com', 'security.wechat.com'},
    'rednote': {f'{host}.{suffix}.com' for host in ('edith', 'www', 'ci', 'rec', 'so')
                for suffix in ('xiaohongshu', 'rnote')},
}


def merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        result = copy.deepcopy(base)
        for key, value in override.items():
            result[key] = merge(result[key], value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(base, list) and isinstance(override, list):
        return copy.deepcopy(override + base)
    return copy.deepcopy(override)


class StashOverridesTests(unittest.TestCase):
    def test_opt_in_scope_and_pins(self):
        manifest = json.loads((DIRECTORY / 'sources.json').read_text())
        files = {p.name for p in DIRECTORY.glob('*.stoverride')}
        self.assertEqual(files, {f'{name}.stoverride' for name in HOSTS})
        self.assertEqual(files, {row['file'] for row in manifest['overrides']})
        names = []
        for row in manifest['overrides']:
            path = DIRECTORY / row['file']
            data = c.load(path)  # Reject duplicate YAML keys as in the profile compiler.
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row['sha256'])
            self.assertEqual(set(data) - METADATA, {'http', 'script-providers'})
            self.assertLessEqual(set(data['http']), {'mitm', 'script', 'mock', 'url-rewrite'})
            self.assertEqual(set(data['http']['mitm']), HOSTS[path.stem])
            self.assertEqual(data['http']['mitm'], row['mitm'])
            self.assertNotIn('#!replace', path.read_text())
            self.assertNotIn('#!append', path.read_text())
            providers = data['script-providers']
            names.extend(providers)
            self.assertEqual({item['name'] for item in data['http']['script']}, set(providers))
            self.assertEqual({p['url'] for p in providers.values()}, {p['url'] for p in row['scripts']})
            for url in (p['url'] for p in providers.values()):
                self.assertRegex(url, r'^https://(?:github\.com/Biliverse/ADBlock/releases/download/v0\.7\.5/|raw\.githubusercontent\.com/(?:ddgksf2013/Scripts|fmz200/wool_scripts)/[0-9a-f]{40}/)')
            for item in data['http']['script']:
                self.assertNotIn('Teenagers', item['match'])
                if 'argument' in item:
                    self.assertIsInstance(item['argument'], str)
                re.compile(item['match'])
        self.assertEqual(len(names), len(set(names)), 'provider names must not collide across overrides')
        wx = c.load(DIRECTORY / 'wx110.stoverride')['http']['script'][0]
        self.assertEqual(wx['argument'], 'useCache=false&forceRedirect=false')
        for host in HOSTS['wx110']:
            self.assertIsNotNone(re.match(wx['match'], f'https://{host}/cgi-bin/mmspamsupport-bin/newredirectconfirmcgi?x=1'))
        for host in ('weixin110Xqq.com', 'securityXwechat.com', 'security.wechat.com.evil.example'):
            self.assertIsNone(re.match(wx['match'], f'https://{host}/cgi-bin/mmspamsupport-bin/newredirectconfirmcgi?x=1'))

    def test_all_subsets_preserve_base_routing_and_do_not_lose_http_entries(self):
        base = c.build('stash')[0]
        overrides = [c.load(DIRECTORY / f'{name}.stoverride') for name in HOSTS]
        # Exercise every ordered subset, including the unchanged base configuration.
        for length in range(4):
            for selected in itertools.permutations(overrides, length):
                combined = copy.deepcopy(base)
                for override in selected:
                    combined = merge(combined, {k: v for k, v in override.items() if k not in METADATA})
                self.assertEqual({k: v for k, v in combined.items() if k not in {'http', 'script-providers'}}, base)
                self.assertEqual(len(combined.get('http', {}).get('script', [])), sum(len(x['http']['script']) for x in selected))
                self.assertEqual(set(combined.get('http', {}).get('mitm', [])), set().union(*(set(x['http']['mitm']) for x in selected)))
