from typing import List

from aqt import mw
from aqt.qt import QTimer
from aqt.toolbar import Toolbar

# === Toolbar Sizing ===
TOOLBAR_HEIGHT = 45

def _enforce_toolbar_height() -> None:
    mw.toolbar.web.setFixedHeight(TOOLBAR_HEIGHT)

# === Toolbar Redraw Helpers ===
def redraw_toolbar() -> None:
    _enforce_toolbar_height()
    mw.toolbar.redraw()
    QTimer.singleShot(0, _enforce_toolbar_height)
    QTimer.singleShot(100, _enforce_toolbar_height)

def redraw_toolbar_legacy(links: List[str], _: Toolbar) -> None:
    _enforce_toolbar_height()
    QTimer.singleShot(0, _enforce_toolbar_height)
    QTimer.singleShot(100, _enforce_toolbar_height)
