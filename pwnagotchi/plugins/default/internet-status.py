"""Show whether the device can reach the internet on the LCD."""

import socket
import threading

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts


class InternetStatus(plugins.Plugin):
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Shows internet connectivity on the display.'

    def __init__(self):
        self._online = False
        self._stop = threading.Event()
        self._worker_thread = None

    def on_loaded(self):
        self._stop.clear()
        self._worker_thread = threading.Thread(target=self._probe_loop, daemon=True)
        self._worker_thread.start()

    def _probe_loop(self):
        while not self._stop.is_set():
            try:
                with socket.create_connection(('1.1.1.1', 53), timeout=2):
                    self._online = True
            except OSError:
                self._online = False
            self._stop.wait(15)

    def on_ui_setup(self, ui):
        position = self.options.get('position', '155,0').split(',')
        x, y = int(position[0]), int(position[1])
        ui.add_element(
            'internet_status',
            LabeledValue(
                color=BLACK,
                label='NET',
                value='OFF',
                position=(x, y),
                label_font=fonts.Bold,
                text_font=fonts.Medium,
            ),
        )

    def on_unload(self, ui):
        self._stop.set()
        if ui.has_element('internet_status'):
            ui.remove_element('internet_status')

    def on_ui_update(self, ui):
        ui.set('internet_status', 'OK' if self._online else 'OFF')
