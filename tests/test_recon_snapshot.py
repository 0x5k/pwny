import json
import tempfile
import unittest
from pathlib import Path
from pwnagotchi.recon import read_snapshot


class SnapshotTest(unittest.TestCase):
    def test_freshness_and_unknown_channel(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'recon.json'
            path.write_text(json.dumps(dict(version=1, source='rust', updated_at=100,
                aps=[dict(channel=6, last_seen=99), dict(channel=None, last_seen=99)])))
            self.assertEqual(len(read_snapshot(path, now=101)['aps']), 1)
            with self.assertRaises(ValueError):
                read_snapshot(path, now=111)
