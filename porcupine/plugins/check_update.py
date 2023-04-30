import requests
from porcupine import __version__ as local_version
from porcupine import get_main_window, images


def check_releases():
    remote_version = requests.get('https://api.github.com/repos/Akuli/porcupine/releases/latest',
                 headers={'Accept': 'application/vnd.github+json'}).json()['tag_name']
    window = get_main_window()
    if local_version != remote_version.strip('v'):
        window.title(f"Porcupine {local_version} - Update Available")
    else:
        window.title(f"Porcupine {local_version}")


def setup() -> None:
    check_releases()
