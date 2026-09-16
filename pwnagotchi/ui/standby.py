"""Live device state for the original UI while the capture agent is stopped."""

import json
from pathlib import Path

from pwnagotchi.ui import faces


def read_radio_status(directory='/var/log/pwnagotchi-diagnostics'):
    for name in ('radio-status.json', 'radio-setup-status.json'):
        try:
            status = json.loads((Path(directory) / name).read_text())
            if isinstance(status, dict):
                return status
        except (OSError, ValueError):
            pass
    return {}


def frame_data(radio, uptime):
    if radio.get('result') == 'ready':
        message = 'Wi-Fi ready. Waiting for my agent.'
    elif radio.get('reason') == 'iw-missing':
        message = 'Waiting for Wi-Fi tools.'
    elif radio.get('reason') in ('internal-interface-missing', 'internal-radio-missing'):
        message = 'Waiting for onboard Wi-Fi.'
    elif radio.get('reason') in (
        'monitor-mode-unsupported', 'internal-monitor-create-failed',
        'internal-monitor-interface-missing',
    ):
        message = 'Wi-Fi needs monitor mode.'
    else:
        message = 'Checking my onboard Wi-Fi.'
    hours, remainder = divmod(max(0, int(uptime)), 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        'face': faces.AWAKE,
        'status': message,
        'mode': 'WAIT',
        'uptime': '%02d:%02d:%02d' % (hours, minutes, seconds),
        'channel': '-',
        'aps': '-',
        'shakes': '-',
    }
