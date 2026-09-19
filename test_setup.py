import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

SETUP = Path(__file__).parent / 'quantum-desktop-setup'

class MigrationTests(unittest.TestCase):
    def test_preserves_existing_config_and_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Path(tmp)
            db = h/'database.db'
            db.write_bytes(b'database sentinel')
            old = h/'old-config.yaml'
            config = dict(server=dict(listen='127.0.0.1', port=8085, database=str(db), sources=[dict(name='Files', path='/example', config=dict(readOnly=False))]), auth=dict(methods=dict(noauth=True)))
            old.write_text(json.dumps(config))
            desktop=h/'.local/share/applications/filebrowser-quantum-local.desktop'
            desktop.parent.mkdir(parents=True)
            desktop.write_text('old desktop')
            with patch.dict(os.environ, HOME=tmp), patch('sys.argv', ['setup','--adopt-config',str(old)]), patch('subprocess.run'), patch('shutil.which', return_value='/usr/bin/edge'), patch('os.getuid', return_value=1000):
                runpy.run_path(str(SETUP),run_name='__main__')
            self.assertEqual(json.loads((h/'.config/quantum-desktop/config.yaml').read_text()), config)
            self.assertEqual(db.read_bytes(), b'database sentinel')
            self.assertFalse(desktop.exists())
            backups=list((h/'.local/state/filebrowser-quantum').glob('package-migration-*/*'))
            self.assertTrue(any(f.read_bytes()==b'database sentinel' for f in backups))
            self.assertIn('/usr/lib/quantum-desktop/filebrowser', (h/'.config/systemd/user/filebrowser-quantum.service').read_text())
            unit = (h/'.config/systemd/user/filebrowser-quantum.service').read_text()
            self.assertIn('WorkingDirectory=' + str(h/'.local/share/filebrowser-quantum') + '\n', unit)

    def test_new_setup_defaults_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=Path(tmp); folder=h/'Notes with spaces';folder.mkdir()
            with patch.dict(os.environ, HOME=tmp), patch('sys.argv',['setup','--folder',str(folder)]), patch('subprocess.run'), patch('shutil.which', return_value='/usr/bin/edge'), patch('os.getuid',return_value=1000):
                runpy.run_path(str(SETUP),run_name='__main__')
            config=json.loads((h/'.config/quantum-desktop/config.yaml').read_text())
            self.assertTrue(config['server']['sources'][0]['config']['readOnly'])
            self.assertEqual(config['server']['listen'],'127.0.0.1')
            self.assertEqual(list(folder.iterdir()),[])

if __name__=='__main__':unittest.main()
