import requests
from porcupine import __version__ as local_version
from porcupine import get_main_window


def get_remote_vers():
    remote = requests.get('https://api.github.com/repos/Akuli/porcupine/releases/latest',
                                  headers={'Accept': 'application/vnd.github+json'}).json()['tag_name']
    return remote.strip('v')

def get_local_vers():
    local = local_version
    return local


def check_releases(local_version: str, remote_version: str) -> bool:
    window = get_main_window()
    if local_version != remote_version:
        window.title(f"Porcupine {local_version} - Update Available")
        return True
    else:
        window.title(f"Porcupine {local_version}")
        return False


def setup() -> None:
    check_releases(get_local_vers(), get_remote_vers())
