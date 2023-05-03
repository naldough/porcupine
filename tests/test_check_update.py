import requests
import re
from porcupine import get_main_window
from porcupine.plugins.check_update import get_remote_vers, get_local_vers, check_releases


def test_check_releases():
    assert not check_releases("2023.03.11", "2023.03.11")   # no update = False
    assert check_releases("2023.03.11", "v2023.03.11")
    assert check_releases(2023, "v2023.03.11")
    assert check_releases("2023.03.11", 03.11)
