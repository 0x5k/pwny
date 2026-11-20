# Pwny

Pwny is a fork of [Pwnagotchi 1.5.5](https://github.com/evilsocket/pwnagotchi) for the Raspberry Pi Zero 2 W and the black-and-white Waveshare 2.13-inch V4 display.

The [Python application](pwnagotchi/) runs the device UI. Its [V4 display driver](pwnagotchi/ui/hw/waveshare2in13_v4.py) draws a full frame at startup and uses partial refreshes for later updates. The [Rust component](rust/README.md) is experimental and the original application can run independently of it.

## Display development

Run the V4 tests from the repository root with Python 3. They exercise the display layout and refresh sequence using a simulated panel.

```sh
python3 -m unittest discover -s tests -p test_waveshare2in13_v4.py
```

The [builder directory](builder/) contains the original Packer setup. The separate Zero 2 W image build recipe is absent from this checkout.

Pwny retains the upstream [GPL license](LICENSE.md).
