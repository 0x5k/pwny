import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from pwnagotchi.utils import total_unique_handshakes, iface_channels


class HandshakeCountTest(unittest.TestCase):
    def test_nl80211_channels_without_iwlist(self):
        with patch('pwnagotchi.utils.shutil.which', side_effect=[None, '/usr/sbin/iw']), \
             patch('pwnagotchi.utils.subprocess.run', side_effect=[
                 SimpleNamespace(stdout='Interface mon0\n\twiphy 0\n'),
                 SimpleNamespace(stdout='* 2412 MHz [1]\n* 2472 MHz [13]\n* 2484 MHz [14] (disabled)\n')]):
            self.assertEqual(iface_channels('mon0'), [1, 13])

    def test_old_and_new_capture_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('old.pcap', 'new.pcapng', 'same.pcap', 'same.pcapng', 'notes.txt'):
                (Path(folder) / name).touch()
            (Path(folder) / 'directory.pcapng').mkdir()
            self.assertEqual(total_unique_handshakes(folder), 3)
            self.assertEqual(total_unique_handshakes(folder + '/missing'), 0)
