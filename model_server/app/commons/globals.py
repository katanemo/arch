import app.commons.utilities as utils


DEVICE = utils.get_device()
MODE = utils.get_serving_mode()
HARDWARE = utils.get_hardware(MODE)
