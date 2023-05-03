"""Set the title and icon of the Porcupine window."""
from porcupine import __version__ as porcupine_version
from porcupine import get_main_window, images


def setup() -> None:
    window = get_main_window()
    window.wm_iconphoto(False, images.get("logo-200x200"))
