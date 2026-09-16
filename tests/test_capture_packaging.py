import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CapturePackagingTest(unittest.TestCase):
    def test_bettercap_wrapper_caplet_is_installed_by_image_recipe(self):
        wrapper = (ROOT / 'image/layer/pwnagotchi-diagnostic/rootfs/usr/local/bin/pwnagotchi-bettercap').read_text()
        self.assertIn('pwnagotchi-api.cap', wrapper)
        recipe = (ROOT / 'image/layer/pwnagotchi-diagnostic.yaml').read_text()
        self.assertIn('pwnagotchi-api.cap', recipe)
        self.assertTrue((ROOT / 'image/layer/pwnagotchi-diagnostic/rootfs/usr/local/share/bettercap/caplets/pwnagotchi-api.cap').is_file())


if __name__ == '__main__':
    unittest.main()
