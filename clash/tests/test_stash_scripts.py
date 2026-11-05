"""Exercise the integrity gate's failure paths without downloading or running JS."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('stash_scripts', ROOT / 'clash/scripts/check_stash_scripts.py')
scripts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scripts)


class StashScriptsTests(unittest.TestCase):
    def test_reviewed_snapshot(self):
        self.assertEqual(scripts.verify(), (4, 1))

    def test_bilibili_error_logging_at_default_level(self):
        subprocess.run(['node', str(ROOT / 'clash/tests/check_bilibili_logging.js')],
                       capture_output=True, check=True)

    def test_rejects_missing_tampered_and_unpinned_dependencies(self):
        for mutation in ('missing', 'tampered', 'unpinned', 'secondary-script'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copytree(ROOT / scripts.SCRIPTS, root / scripts.SCRIPTS)
                shutil.copytree(ROOT / scripts.OVERRIDES, root / scripts.OVERRIDES)
                (root / '.git').symlink_to(ROOT / '.git', target_is_directory=True)
                snapshot_path = root / scripts.SCRIPTS / 'snapshot.json'
                snapshot = json.loads(snapshot_path.read_text())
                asset = root / scripts.SCRIPTS / snapshot['assets'][0]['path']
                if mutation == 'missing':
                    asset.unlink()
                elif mutation == 'tampered':
                    asset.write_bytes(asset.read_bytes() + b'\n// injected\n')
                elif mutation == 'secondary-script':
                    snapshot['assets'][0]['runtime_script_dependencies'] = ['https://example.invalid/loader.js']
                    snapshot_path.write_text(json.dumps(snapshot))
                else:
                    manifest_path = root / scripts.OVERRIDES / 'sources.json'
                    manifest = json.loads(manifest_path.read_text())
                    manifest['overrides'][0]['scripts'][0]['url'] = 'https://example.invalid/latest.js'
                    manifest_path.write_text(json.dumps(manifest))
                with self.assertRaises((ValueError, FileNotFoundError)):
                    scripts.verify(root)
