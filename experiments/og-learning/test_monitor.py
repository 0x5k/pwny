"""Exercise fail-closed preconditions without starting a service or touching a Pi."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('pi_monitor', Path(__file__).with_name('pi_monitor.py'))
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class Preconditions(unittest.TestCase):
    def run_case(self, *, available=240 * 1024, swap=0, active='active', oom=(0, 0)):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'results'
            state = dict(ActiveState=active, NRestarts='0')
            original_read = Path.read_text

            def read(path, *args, **kwargs):
                if str(path) == '/proc/device-tree/model':
                    return 'Simulated Pi\x00'
                return original_read(path, *args, **kwargs)

            with patch('sys.argv', ['pi_monitor.py', directory, str(output)]), \
                 patch.object(monitor, 'properties', return_value=state), \
                 patch.object(monitor, 'memory', return_value=dict(MemAvailable=available, SwapTotal=swap)), \
                 patch.object(monitor, 'oom_kills', side_effect=oom), \
                 patch.object(monitor.subprocess, 'Popen') as start, \
                 patch.object(Path, 'read_text', read), \
                 patch('builtins.print'):
                with self.assertRaises(SystemExit) as result:
                    monitor.main()
                self.assertEqual(result.exception.code, 1)
                start.assert_not_called()
            return json.loads((output / 'pi-monitor.json').read_text())

    def test_swap_rejected_without_launch(self):
        self.assertIn('swap is configured', self.run_case(swap=1024)['failure'])

    def test_inactive_service_rejected_without_launch(self):
        self.assertIn('not active', self.run_case(active='failed')['failure'])

    def test_insufficient_memory_rejected_without_launch(self):
        self.assertIn('insufficient', self.run_case(available=100 * 1024)['failure'])

    def test_global_oom_is_recorded_even_on_preflight_failure(self):
        report = self.run_case(swap=1024, oom=(10, 11))
        self.assertEqual(report['oom_kills_delta'], 1)
        self.assertEqual(report['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
