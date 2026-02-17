from typing import Any, Optional

# === Startup Side Effects ===
from .utils import dialog

# === Core Utilities ===
from .utils.css_files import css_files_dir
from .utils.logger import logger
from .utils.modules import *
from .utils.themes import get_theme, normalize_theme_name

# === Anki/Qt Imports ===
from aqt import AnkiQt, DialogManager, QWidget, gui_hooks, mw
from aqt.theme import theme_manager

# === Dialog Windows ===
if module_exists("aqt.browser.browser"):
    from aqt.browser.browser import Browser
else:
    from aqt.browser import Browser
if module_has_attribute("aqt.stats", "NewDeckStats"):
    from aqt.stats import DeckStats, NewDeckStats
else:
    from aqt.stats import DeckStats
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.about import ClosableQDialog
from aqt.preferences import Preferences
from aqt.addons import AddonsDialog
if module_exists("aqt.filtered_deck"):
    from aqt.filtered_deck import FilteredDeckConfigDialog

# === Webview Contexts ===
from aqt.toolbar import TopToolbar
from aqt.deckbrowser import DeckBrowser, DeckBrowserBottomBar
from aqt.overview import Overview, OverviewBottomBar
from aqt.editor import Editor
from aqt.reviewer import Reviewer, ReviewerBottomBar
from aqt.webview import WebContent

from anki.utils import pointVersion

# === Styling Injections ===
from .injections.toolbar import redraw_toolbar_legacy

# === Config ===
from .config import get_config

# === Theme/Style State ===
logger.debug(css_files_dir)
LIGHT_COLOR_MODE = 2
DARK_COLOR_MODE = 3


def get_effective_color_mode() -> int:
    return DARK_COLOR_MODE if theme_manager.get_night_mode() else LIGHT_COLOR_MODE


def get_active_theme_name(config_data: dict) -> str:
    return normalize_theme_name(config_data.get("theme_name", "Anki"))


initial_config = get_config()
themes_parsed = get_theme(get_active_theme_name(initial_config))
color_mode = get_effective_color_mode()

# === Title Bar Styling ===
from .utils.dark_title_bar import set_dark_titlebar, set_dark_titlebar_qt, dwmapi
set_dark_titlebar(mw, dwmapi)
logger.debug(dwmapi)

# === CSS Injection Helpers ===
def load_custom_style(include_typography: bool = True):
    current_config = get_config()

    theme_colors_light = ""
    theme_colors_dark = ""
    for color_name in themes_parsed.get("colors"):
        color = themes_parsed.get("colors").get(color_name)
        if color[-1]:
            theme_colors_light += f"{color[-1]}: {color[LIGHT_COLOR_MODE]};\n        "
            theme_colors_dark += f"{color[-1]}: {color[DARK_COLOR_MODE]};\n        "
        else:
            theme_colors_light += f"--{color_name.lower().replace('_','-')}: {color[LIGHT_COLOR_MODE]};\n        "
            theme_colors_dark += f"--{color_name.lower().replace('_','-')}: {color[DARK_COLOR_MODE]};\n        "
    typography_css = ""
    if include_typography and current_config.get("font_customization_enabled", False):
        font = current_config["font"]
        if current_config["fallbackFonts"]:
            font = f"{current_config['font']}, {current_config['fallbackFonts']}"
        typography_css = """
    html {
        font-family: %s;
        font-size: %spx !important;
        --font-size: %spx !important;
    }
""" % (font, current_config["font_size"], current_config["font_size"])
    custom_style = """
<style>
    /* Light */ 
    :root,
    :root .isMac,
    :root .isWin,
    :root .isLin {
        %s
    }
    /* Dark */
    :root body.nightMode,
    :root body.isWin.nightMode,
    :root body.isMac.nightMode,
    :root body.isLin.nightMode {
        %s
    }
%s
</style>
    """ % (theme_colors_light, theme_colors_dark, typography_css)
    return custom_style


def load_custom_style_wrapper():
    custom_style = f"""
    const style = document.createElement("style");
    style.innerHTML = `{load_custom_style()[8:-13]}`;
    document.head.appendChild(style);
    """
    return custom_style

# === Webview Styling Hook ===
def on_webview_will_set_content(web_content: WebContent, context: Optional[Any]) -> None:
    logger.debug(context)
    is_card_rendering_context = (
        isinstance(context, Reviewer)
        or context_name_includes(context, "aqt.clayout.CardLayout")
        or context_name_includes(context, "Previewer")
    )
    web_content.css.append(css_files_dir['global'])
    web_content.head += load_custom_style(include_typography=not is_card_rendering_context)
    if isinstance(context, DeckBrowser):
        web_content.css.append(css_files_dir['DeckBrowser'])
    elif isinstance(context, TopToolbar):
        web_content.css.append(css_files_dir['TopToolbar'])
    elif isinstance(context, DeckBrowserBottomBar) or isinstance(context, OverviewBottomBar):
        web_content.css.append(css_files_dir['BottomBar'])
    elif isinstance(context, Overview):
        web_content.css.append(css_files_dir['Overview'])
    elif isinstance(context, Editor):
        web_content.css.append(css_files_dir['Editor'])
    elif isinstance(context, Reviewer):
        web_content.css.append(css_files_dir['Reviewer'])
    elif isinstance(context, ReviewerBottomBar):
        web_content.css.append(css_files_dir['BottomBar'])
        web_content.css.append(css_files_dir['ReviewerBottomBar'])
        web_content.body += "<div style='height: 14px; opacity: 0; pointer-events: none;'></div>"
        web_content.body += "<div id='padFix' style='height: 30px; opacity: 0; pointer-events: none;'><script>const e = document.getElementById('padFix');e.parentElement.removeChild(e);</script></div>"
        if pointVersion() >= 56:
            web_content.body = "<div class='new-qt6' style='display: none;'></div>"+web_content.body
        mw.bottomWeb.adjustHeightToFit()
    elif context_name_includes(context, "aqt.clayout.CardLayout"):
        web_content.css.append(css_files_dir['CardLayout'])
    elif context_name_includes(context, "aqt.main.ResetRequired"):
        web_content.css.append(css_files_dir['legacy'])


# === Hook Wiring ===
gui_hooks.webview_will_set_content.append(on_webview_will_set_content)

if attribute_exists(gui_hooks, "main_window_did_init"):
    pass
elif attribute_exists(gui_hooks, "top_toolbar_did_init_links"):
    gui_hooks.top_toolbar_did_init_links.append(redraw_toolbar_legacy)

# === Dialog Styling Hook ===
def on_dialog_manager_did_open_dialog(dialog_manager: DialogManager, dialog_name: str, dialog_instance: QWidget) -> None:
    logger.debug(dialog_name)
    dialog: AnkiQt = dialog_manager._dialogs[dialog_name][1]
    set_dark_titlebar_qt(dialog, dwmapi)
    if dialog_name == "AddCards":
        context: AddCards = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QAddCards'], encoding='utf-8').read())
    elif dialog_name == "AddonsDialog":
        context: AddonsDialog = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QAddonsDialog'], encoding='utf-8').read())
    elif dialog_name == "Browser":
        context: Browser = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QBrowser'], encoding='utf-8').read())
    elif dialog_name == "EditCurrent":
        context: EditCurrent = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QEditCurrent'], encoding='utf-8').read())
    elif module_exists("aqt.filtered_deck") and dialog_name == "FilteredDeckConfigDialog":
        context: FilteredDeckConfigDialog = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QFilteredDeckConfigDialog'], encoding='utf-8').read())
    elif dialog_name == "NewDeckStats":
        context: NewDeckStats = dialog_manager._dialogs[dialog_name][1]
        context.form.web.eval(load_custom_style_wrapper())
        context.setStyleSheet(open(css_files_dir['QNewDeckStats'], encoding='utf-8').read())
    elif dialog_name == "About":
        context: ClosableQDialog = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QAbout'], encoding='utf-8').read())
    elif dialog_name == "Preferences":
        context: Preferences = dialog_manager._dialogs[dialog_name][1]
        context.setStyleSheet(open(css_files_dir['QPreferences'], encoding='utf-8').read())
    elif dialog_name == "sync_log":
        pass


if attribute_exists(gui_hooks, "dialog_manager_did_open_dialog"):
    gui_hooks.dialog_manager_did_open_dialog.append(
        on_dialog_manager_did_open_dialog)
else:
    # === Legacy Dialog Styling ===
    def monkey_setup_dialog_gc(obj: Any) -> None:
        obj.finished.connect(lambda: mw.gcWindow(obj))
        logger.debug(obj)
        set_dark_titlebar_qt(obj, dwmapi)
        if isinstance(obj, AddCards):
            obj.setStyleSheet(open(css_files_dir['QAddCards'], encoding='utf-8').read())
        elif isinstance(obj, EditCurrent):
            obj.setStyleSheet(open(css_files_dir['QEditCurrent'], encoding='utf-8').read())
        elif isinstance(obj, DeckStats):
            obj.setStyleSheet(open(css_files_dir['QNewDeckStats'], encoding='utf-8').read())
        elif isinstance(obj, ClosableQDialog):
            obj.setStyleSheet(open(css_files_dir['QAbout'], encoding='utf-8').read())

    mw.setupDialogGC = monkey_setup_dialog_gc

    if attribute_exists(gui_hooks, "addons_dialog_will_show"):
        def on_addons_dialog_will_show(dialog: AddonsDialog) -> None:
            logger.debug(dialog)
            set_dark_titlebar_qt(dialog, dwmapi)
            dialog.setStyleSheet(open(css_files_dir['QAddonsDialog'], encoding='utf-8').read())
        gui_hooks.addons_dialog_will_show.append(on_addons_dialog_will_show)
    if attribute_exists(gui_hooks, "browser_will_show"):
        def on_browser_will_show(browser: Browser) -> None:
            logger.debug(browser)
            set_dark_titlebar_qt(browser, dwmapi)
            browser.setStyleSheet(open(css_files_dir['QBrowser'], encoding='utf-8').read())
        gui_hooks.browser_will_show.append(on_browser_will_show)

# === Theme Change Wiring ===
if attribute_exists(gui_hooks, "style_did_init"):
    def updateStyle(str):
        return str
    gui_hooks.style_did_init.append(updateStyle)

def updateTheme(_):
    logger.debug("updating theme")
    global themes_parsed, color_mode
    current_config = get_config()
    themes_parsed = get_theme(get_active_theme_name(current_config))
    color_mode = get_effective_color_mode()


# Communication through script using rarely used hook (might change to custom hooks in the future)
gui_hooks.debug_console_will_show.append(updateTheme)
