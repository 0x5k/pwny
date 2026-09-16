import sys
import types
import unittest


# Keep the hardware backend tests runnable on build hosts without Pillow. The
# real image installs python3-pil; these stubs only cover font construction used
# while laying out the UI.
if "PIL" not in sys.modules:
    pil = types.ModuleType("PIL")
    image_font = types.ModuleType("PIL.ImageFont")

    class FakeFont:
        def __init__(self, size):
            self.size = size

    image_font.truetype = lambda name, size: FakeFont(size)
    pil.ImageFont = image_font
    sys.modules["PIL"] = pil
    sys.modules["PIL.ImageFont"] = image_font

import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.hw import display_for
from pwnagotchi.ui.hw.waveshare2in13_v4 import Waveshare2in13V4


class FakeCanvas:
    def __init__(self):
        self.conversions = []

    def convert(self, mode):
        self.conversions.append(mode)
        return self


class FakeEPD:
    def __init__(self, init_result=0):
        self.calls = []
        self.init_result = init_result

    def init(self):
        self.calls.append(("init",))
        return self.init_result

    def Clear(self, color):
        self.calls.append(("Clear", color))

    def getbuffer(self, canvas):
        self.calls.append(("getbuffer", canvas))
        return b"frame"

    def displayPartBaseImage(self, buffer):
        self.calls.append(("displayPartBaseImage", buffer))

    def display(self, buffer):
        self.calls.append(("display", buffer))

    def displayPartial(self, buffer):
        self.calls.append(("displayPartial", buffer))

    def sleep(self):
        self.calls.append(("sleep",))


class Waveshare2in13V4Test(unittest.TestCase):
    def setUp(self):
        fonts.STATUS_FONT_NAME = "DejaVuSansMono"
        fonts.SIZE_OFFSET = 0
        fonts.setup(10, 9, 10, 35, 25, 9)
        self.config = {
            "ui": {
                "display": {
                    "color": "black",
                    "type": "waveshare_2in13_v4",
                }
            }
        }

    def install_fake_driver(self, driver):
        package = types.ModuleType("waveshare_epd")
        module = types.ModuleType("waveshare_epd.epd2in13_V4")
        module.EPD = lambda: driver
        package.epd2in13_V4 = module
        sys.modules["waveshare_epd"] = package
        sys.modules["waveshare_epd.epd2in13_V4"] = module

    def tearDown(self):
        sys.modules.pop("waveshare_epd", None)
        sys.modules.pop("waveshare_epd.epd2in13_V4", None)

    def test_layout_and_dispatch_use_the_v2_compatible_geometry(self):
        implementation = display_for(self.config)
        self.assertIsInstance(implementation, Waveshare2in13V4)
        self.assertEqual("waveshare_2in13_v4", implementation.name)

        layout = implementation.layout()
        self.assertEqual(250, layout["width"])
        self.assertEqual(122, layout["height"])
        self.assertEqual([0, 108, 250, 108], layout["line2"])

    def test_first_render_seeds_both_ram_banks_then_uses_partial_refresh(self):
        driver = FakeEPD()
        self.install_fake_driver(driver)
        implementation = Waveshare2in13V4(self.config)
        canvas = FakeCanvas()

        implementation.initialize()
        implementation.render(canvas)
        implementation.render(canvas)

        methods = [call[0] for call in driver.calls]
        self.assertEqual(
            [
                "init",
                "Clear",
                "getbuffer",
                "display",
                "displayPartBaseImage",
                "getbuffer",
                "displayPartial",
            ],
            methods,
        )
        self.assertEqual(["1", "1"], canvas.conversions)

    def test_clear_requires_a_new_base_frame_and_sleep_releases_driver(self):
        driver = FakeEPD()
        self.install_fake_driver(driver)
        implementation = Waveshare2in13V4(self.config)
        canvas = FakeCanvas()

        implementation.initialize()
        implementation.render(canvas)
        implementation.clear()
        implementation.render(canvas)
        implementation.sleep()

        methods = [call[0] for call in driver.calls]
        self.assertEqual(2, methods.count("displayPartBaseImage"))
        self.assertEqual(2, methods.count("display"))
        self.assertEqual(2, methods.count("Clear"))
        self.assertEqual("sleep", methods[-1])
        with self.assertRaisesRegex(RuntimeError, "not initialized"):
            implementation.render(canvas)

    def test_initialization_error_is_reported(self):
        driver = FakeEPD(init_result=-1)
        self.install_fake_driver(driver)
        implementation = Waveshare2in13V4(self.config)

        with self.assertRaisesRegex(RuntimeError, "initialization returned -1"):
            implementation.initialize()


if __name__ == "__main__":
    unittest.main()
