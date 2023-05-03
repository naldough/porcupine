from porcupine import settings, menubar, tabs, get_tab_manager
from porcupine.settings import global_settings

def bind_quit() -> None:
    if not global_settings.get("ctrl-q_quit", bool):
        menubar.set_enabled_based_on_tab("File/Quit", (lambda tab: (isinstance(tab, tabs.FileTab) or tab is None)))
    else:
        menubar.set_enabled_based_on_tab("File/Quit", (lambda tab: tab is None))

def on_new_filetab(tab: tabs.FileTab) -> None:
    tab.bind("<<GlobalSettingChanged:ctrl-q_quit>>", lambda event: bind_quit(), add=True)

def setup() -> None:
    global_settings.add_option("ctrl-q_quit", default=True)
    settings.add_checkbutton("ctrl-q_quit", text="ctrl-q quit when no tabs are open")
    get_tab_manager().add_filetab_callback(on_new_filetab)
    bind_quit()
