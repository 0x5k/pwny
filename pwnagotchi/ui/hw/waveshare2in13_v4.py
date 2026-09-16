import logging
import threading

import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.hw.base import DisplayImpl


class Waveshare2in13V4(DisplayImpl):
    """Waveshare 2.13-inch V4 black/white e-paper display."""

    def __init__(self, config):
        super(Waveshare2in13V4, self).__init__(config, 'waveshare_2in13_v4')
        self._display = None
        self._base_frame_written = False
        self._io_lock = threading.Lock()

    def layout(self):
        # The V4 panel is 250x122 in landscape and uses the proven Waveshare V2
        # Pwnagotchi layout. It is a black/white panel regardless of the generic
        # ui.display.color setting.
        fonts.setup(10, 9, 10, 35, 25, 9)
        self._layout['width'] = 250
        self._layout['height'] = 122
        self._layout['face'] = (0, 40)
        self._layout['name'] = (5, 20)
        self._layout['channel'] = (0, 0)
        self._layout['aps'] = (28, 0)
        self._layout['uptime'] = (185, 0)
        self._layout['line1'] = [0, 14, 250, 14]
        self._layout['line2'] = [0, 108, 250, 108]
        self._layout['friend_face'] = (0, 92)
        self._layout['friend_name'] = (40, 94)
        self._layout['shakes'] = (0, 109)
        self._layout['mode'] = (225, 109)
        self._layout['status'] = {
            'pos': (125, 20),
            'font': fonts.status_font(fonts.Medium),
            'max': 20
        }
        return self._layout

    def initialize(self):
        logging.info("initializing Waveshare 2.13-inch V4 display")
        from waveshare_epd import epd2in13_V4

        with self._io_lock:
            self._display = epd2in13_V4.EPD()
            result = self._display.init()
            if result not in (0, None):
                self._display = None
                raise RuntimeError(
                    "Waveshare 2.13-inch V4 initialization returned %r" % result
                )
            self._display.Clear(0xFF)
            self._base_frame_written = False

    def render(self, canvas):
        with self._io_lock:
            if self._display is None:
                raise RuntimeError("Waveshare 2.13-inch V4 is not initialized")

            buffer = self._display.getbuffer(canvas.convert('1'))
            if self._base_frame_written:
                self._display.displayPartial(buffer)
            else:
                # Start the live UI with the same true full refresh used by the
                # hardware diagnostic.  Some V4 controllers remain black when
                # the first post-init frame is sent only through the partial
                # update path.  Then seed both RAM banks for later partials.
                self._display.display(buffer)
                self._display.displayPartBaseImage(buffer)
                self._base_frame_written = True

    def clear(self):
        with self._io_lock:
            if self._display is not None:
                self._display.Clear(0xFF)
                self._base_frame_written = False

    def sleep(self):
        with self._io_lock:
            if self._display is not None:
                self._display.sleep()
                self._display = None
                self._base_frame_written = False
