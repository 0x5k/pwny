"""Exercise OG's real event handler with isolated state, never the live agent."""
import json
import unittest
from unittest.mock import Mock, patch

from pwnagotchi.agent import Agent


class HandshakeEventTest(unittest.IsolatedAsyncioTestCase):
    async def test_event_updates_plugins_counter_and_deduplicates(self):
        agent = object.__new__(Agent)
        agent._handshakes = {}
        agent._last_pwnd = None
        ap = dict(mac='02:00:00:00:00:01', hostname='test-lab', channel=6,
                  rssi=-45, vendor='', clients=[])
        agent.session = Mock(return_value={'wifi': {'aps': [ap]}})
        agent._update_handshakes = Mock()
        event = json.dumps(dict(tag='wifi.client.handshake', data=dict(
            file='/test-only/test-lab.pcapng', ap=ap['mac'],
            station='02:00:00:00:00:02', full=True, half=True)))
        with patch('pwnagotchi.agent.plugins.on') as plugin:
            await agent._on_event(event)
            self.assertEqual(agent._last_pwnd, 'test-lab')
            agent._update_handshakes.assert_called_with(1)
            self.assertEqual(plugin.call_count, 1)
            self.assertEqual(plugin.call_args.args[0], 'handshake')
            self.assertEqual(plugin.call_args.args[2], '/test-only/test-lab.pcapng')
            await agent._on_event(event)
            agent._update_handshakes.assert_called_with(0)
            self.assertEqual(plugin.call_count, 1)
            self.assertEqual(len(agent._handshakes), 1)
