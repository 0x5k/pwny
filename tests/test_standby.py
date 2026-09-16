import tempfile
import unittest
from pathlib import Path

from pwnagotchi.ui import faces
from pwnagotchi.ui.standby import frame_data, read_radio_status


class StandbyTest(unittest.TestCase):
    def test_waiting_face_reports_real_uptime_without_capture_statistics(self):
        state = frame_data({'reason': 'monitor-mode-unsupported'}, 3723)
        self.assertEqual(faces.AWAKE, state['face'])
        self.assertEqual('01:02:03', state['uptime'])
        self.assertEqual('WAIT', state['mode'])
        self.assertIn('monitor mode', state['status'])
        self.assertEqual('-', state['aps'])
        self.assertEqual('-', state['shakes'])

    def test_monitor_ready_does_not_claim_agent_is_running(self):
        state = frame_data({'result': 'ready'}, 10)
        self.assertEqual('Wi-Fi ready. Waiting for my agent.', state['status'])
        self.assertEqual('WAIT', state['mode'])

    def test_missing_or_partial_status_does_not_break_the_display(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual({}, read_radio_status(directory))
            (Path(directory) / 'radio-status.json').write_text('{')
            (Path(directory) / 'radio-setup-status.json').write_text(
                '{"result":"blocked","reason":"internal-radio-missing"}')
            state = frame_data(read_radio_status(directory), 0)
            self.assertEqual('Waiting for onboard Wi-Fi.', state['status'])


if __name__ == '__main__':
    unittest.main()
