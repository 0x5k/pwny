from PIL import ImageFont

# should not be changed
FONT_NAME = 'DejaVuSansMono'

# can be changed
STATUS_FONT_NAME = None
SIZE_OFFSET = 0

Bold = None
BoldSmall = None
BoldBig = None
Medium = None
Small = None
Huge = None


def init(config):
    global STATUS_FONT_NAME, SIZE_OFFSET
    STATUS_FONT_NAME = config['ui']['font']['name']
    SIZE_OFFSET = config['ui']['font']['size_offset']
    setup(10, 8, 10, 25, 25, 9)


def status_font(old_font):
    global STATUS_FONT_NAME, SIZE_OFFSET
    return _font(STATUS_FONT_NAME, old_font.size + SIZE_OFFSET)


def _font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        # Minimal images may not ship the optional DejaVu font files. Pillow's
        # built-in bitmap font keeps the UI usable and observable.
        return ImageFont.load_default()


def setup(bold, bold_small, medium, huge, bold_big, small):
    global Bold, BoldSmall, Medium, Huge, BoldBig, Small, FONT_NAME

    Small = _font(FONT_NAME, small)
    Medium = _font(FONT_NAME, medium)
    BoldSmall = _font("%s-Bold" % FONT_NAME, bold_small)
    Bold = _font("%s-Bold" % FONT_NAME, bold)
    BoldBig = _font("%s-Bold" % FONT_NAME, bold_big)
    Huge = _font("%s-Bold" % FONT_NAME, huge)
