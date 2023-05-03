from porcupine import get_main_window, __version__ as local_version
from porcupine.plugins.check_update import check_releases

# tests to check for the versions matching a specific regex patterns made workflow scripts throw errors
def test_check_releases():
    assert not check_releases("2023.03.11", "2023.03.11")   # no update = False
    assert check_releases("2023.03.11", "v2023.03.11")
    assert check_releases(2023, "v2023.03.11")
    assert check_releases("2023.03.11", 03.11)

def test_check_status_bar():
    window = get_main_window()
    check_releases("2023.03.11", "2023.03.11")
    assert window.title() == f"Porcupine {local_version}"
    check_releases("2023.03.11", "v2023.03.11")
    assert window.title() == f"Porcupine {local_version} - Update Available"
