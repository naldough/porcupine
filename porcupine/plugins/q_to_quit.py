from porcupine import settings
from porcupine.settings import global_settings

def setup() -> None:
    global_settings.add_option("ctrl-q_quit", default=True)
    settings.add_checkbutton("ctrl-q_quit", text="ctrl-q quit when no tabs are open")
