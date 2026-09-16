import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / (
    'image/layer/pwnagotchi-diagnostic/rootfs/usr/local/bin/pwnagotchi-radio-preflight')

FAKE_RADIO = r'''
iw() {
    case "$*" in
        'dev wlan0 info') printf 'Interface wlan0\n\ttype managed\n\twiphy 0\n' ;;
        'dev mon0 info') printf 'Interface mon0\n\ttype %s\n\twiphy %s\n' "$TEST_TYPE" "$TEST_PHY" ;;
        'dev mon1 info') return 1 ;;
        'phy phy0 info'|'phy phy1 info')
            if [ "$TEST_SUPPORTED" = yes ]; then printf '\t * monitor\n'; fi ;;
        *) return 1 ;;
    esac
}
ip() { printf '3: mon0: <%s> mtu 1500 state UNKNOWN\n' "$TEST_FLAGS"; }
source "$1"
'''


class RadioPreflightTest(unittest.TestCase):
    def check_radio(self, expected, **changes):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PWN_DIAGNOSTICS_DIR=directory,
                       TEST_TYPE='monitor', TEST_PHY='0', TEST_SUPPORTED='yes',
                       TEST_FLAGS='BROADCAST,MULTICAST,UP,LOWER_UP')
            env.update(changes)
            result = subprocess.run(['bash', '-c', FAKE_RADIO, 'test', str(SCRIPT)],
                                    env=env, text=True, capture_output=True)
            status = json.loads((Path(directory) / 'radio-status.json').read_text())
            self.assertEqual(expected, status['reason'], result.stderr)
            self.assertEqual(0 if expected == 'internal-monitor-ready' else 1,
                             result.returncode, result.stderr)

    def test_onboard_monitor_up_is_ready(self):
        self.check_radio('internal-monitor-ready')

    def test_wrong_radio_cannot_impersonate_the_internal_monitor(self):
        self.check_radio('internal-monitor-interface-missing', TEST_PHY='1')

    def test_managed_interface_named_mon0_is_not_ready(self):
        self.check_radio('internal-monitor-interface-missing', TEST_TYPE='managed')

    def test_down_interface_is_not_ready(self):
        self.check_radio('internal-monitor-interface-missing', TEST_FLAGS='BROADCAST,MULTICAST')

    def test_unsupported_firmware_is_reported(self):
        self.check_radio('monitor-mode-unsupported', TEST_SUPPORTED='no')


if __name__ == '__main__':
    unittest.main()
