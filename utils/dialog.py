import json

# === Anki/Qt Imports ===
from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.theme import colors, theme_manager
from aqt.utils import showInfo
from aqt.webview import AnkiWebView
from anki.utils import pointVersion

# === Local Imports ===
from ..config import config, get_config, write_config
from ..injections.toolbar import redraw_toolbar, redraw_toolbar_legacy
from .dark_title_bar import dwmapi, set_dark_titlebar_qt
from .logger import logger
from .modules import *
from .themes import (
    ensure_user_theme,
    get_system_theme,
    get_theme,
    list_system_theme_names,
    normalize_theme_name,
    write_theme,
)
from .translation import get_texts

# === Language Support ===
if module_has_attribute("anki.lang", "current_lang"):
    from anki.lang import current_lang, lang_to_disk_lang, compatMap
else:
    from anki.lang import currentLang as current_lang, lang_to_disk_lang, compatMap

# === Dialog Constants ===
MIN_WIDTH = 537
MIN_HEIGHT = 589

# === Theme State ===
LIGHT_COLOR_MODE = 2
DARK_COLOR_MODE = 3

THEME_PREVIEW_TAGLINES = {
    "Anki": "Default balanced palette",
    "Evergreen": "Calm moss and pine tones",
    "Graphite": "Refined slate neutrals",
    "Nord": "Cool arctic blue-greys",
    "Sakura": "Soft rose and plum tones",
    "Solarized": "Warm parchment and teal",
    "Sunset": "Muted terracotta warmth",
}


def get_effective_color_mode() -> int:
    return DARK_COLOR_MODE if theme_manager.get_night_mode() else LIGHT_COLOR_MODE


def get_active_theme_name(config_data: dict) -> str:
    return normalize_theme_name(config_data.get("theme_name", "Anki"))


initial_config = get_config()
themes_parsed = get_theme(get_active_theme_name(initial_config))
color_mode = get_effective_color_mode()

# === Language Utilities ===
def get_anki_lang():
    lang = lang_to_disk_lang(current_lang)
    if lang in compatMap:
        lang = compatMap[lang]
    lang = lang.replace("-", "_")
    return lang

# === Theme Editor Dialog ===
class AnkiRedesignThemeEditor(QDialog):
    def __init__(self, parent, theme_name: str, *args, **kwargs):
        super().__init__(parent=parent or mw, *args, **kwargs)
        self.config_editor = parent
        self.theme_name = normalize_theme_name(theme_name)
        self.user_theme_path = ensure_user_theme(self.theme_name)
        self.texts = get_texts(get_anki_lang())
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(f"{self.texts['theme_editor_window_title']} ({self.theme_name})")
        self.setSizePolicy(self.make_size_policy())
        # self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(MIN_WIDTH, MIN_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        set_dark_titlebar_qt(self, dwmapi, fix=False)
        # Root layout
        self.root_layout = QVBoxLayout(self)
        # Main layout
        self.layout = QVBoxLayout()
        self.textedit = QTextEdit()
        themes_plaintext = open(self.user_theme_path, encoding="utf-8").read()
        self.textedit.setPlainText(themes_plaintext)
        self.layout.addWidget(self.textedit)
        self.root_layout.addLayout(self.layout)
        self.root_layout.addLayout(self.make_button_box())

    def save_edit(self) -> None:
        themes_parsed = json.loads(self.textedit.toPlainText())
        write_theme(self.user_theme_path, themes_parsed)
        self.config_editor.update()
        self.accept()

    def make_button_box(self) -> QWidget:
        def cancel():
            button = QPushButton(self.texts["cancel_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            qconnect(button.clicked, self.accept)
            return button

        def save():
            button = QPushButton(self.texts["save_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            button.setDefault(True)
            button.setShortcut("Ctrl+Return")
            button.clicked.connect(lambda _: self.save_edit())
            return button

        button_box = QHBoxLayout()
        button_box.addStretch()
        button_box.addWidget(cancel())
        button_box.addWidget(save())
        return button_box

    def make_size_policy(self) -> QSizePolicy:
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        return size_policy

# === Configuration Dialog ===
class AnkiRedesignConfigDialog(QDialog):
    def __init__(self, parent: QWidget, *args, **kwargs):
        super().__init__(parent=parent or mw, *args, **kwargs)
        self.texts = get_texts(get_anki_lang())
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(self.texts["configuration_window_title"])
        self.setSizePolicy(self.make_size_policy())
        # self.setMinimumSize(420, 580)
        # self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(MIN_WIDTH, MIN_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        set_dark_titlebar_qt(self, dwmapi, fix=False)

        # Theme color state
        self.current_config = get_config()
        self.available_themes = list_system_theme_names()
        self.theme_name = get_active_theme_name(self.current_config)
        if self.theme_name not in self.available_themes and self.available_themes:
            self.theme_name = self.available_themes[0]
        if not self.available_themes:
            self.available_themes = [self.theme_name]

        global themes_parsed, color_mode
        themes_parsed = get_theme(self.theme_name)
        color_mode = get_effective_color_mode()
        self.theme_colors = themes_parsed.get("colors")
        self.updates = []
        self.theme_general = ["TEXT_FG", "WINDOW_BG", "FRAME_BG", "BUTTON_BG", "BUTTON_FOCUS_BG", "TOOLTIP_BG", "BORDER", "MEDIUM_BORDER", "FAINT_BORDER", "HIGHLIGHT_BG", "HIGHLIGHT_FG" , "LINK", "DISABLED", "SLIGHTLY_GREY_TEXT", "FOCUS_SHADOW"]
        self.theme_decks = ["CURRENT_DECK", "NEW_COUNT", "LEARN_COUNT", "REVIEW_COUNT", "ZERO_COUNT"]
        self.theme_browse = ["BURIED_FG", "SUSPENDED_FG", "MARKED_BG", "FLAG1_BG", "FLAG1_FG", "FLAG2_BG", "FLAG2_FG", "FLAG3_BG", "FLAG3_FG", "FLAG4_BG", "FLAG4_FG", "FLAG5_BG", "FLAG5_FG", "FLAG6_BG", "FLAG6_FG", "FLAG7_BG", "FLAG7_FG"]
        self.theme_extra = []
        if pointVersion() >= 56:
            self.theme_general = ['FG', 'FG_DISABLED', 'FG_FAINT', 'FG_LINK', 'FG_SUBTLE'] + ['CANVAS', 'CANVAS_CODE', 'CANVAS_ELEVATED', 'CANVAS_INSET', 'CANVAS_OVERLAY']
            self.theme_decks = ['BORDER', 'BORDER_FOCUS', 'BORDER_STRONG', 'BORDER_SUBTLE'] + ['BUTTON_BG', 'BUTTON_DISABLED', 'BUTTON_GRADIENT_END', 'BUTTON_GRADIENT_START', 'BUTTON_HOVER_BORDER', 'BUTTON_PRIMARY_BG', 'BUTTON_PRIMARY_DISABLED', 'BUTTON_PRIMARY_GRADIENT_END', 'BUTTON_PRIMARY_GRADIENT_START']
            self.theme_browse = ['ACCENT_CARD', 'ACCENT_DANGER', 'ACCENT_NOTE'] + ['STATE_BURIED', 'STATE_LEARN', 'STATE_MARKED', 'STATE_NEW', 'STATE_REVIEW', 'STATE_SUSPENDED'] + ['FLAG_1', 'FLAG_2', 'FLAG_3', 'FLAG_4', 'FLAG_5', 'FLAG_6', 'FLAG_7']
            self.theme_extra = ['SCROLLBAR_BG', 'SCROLLBAR_BG_ACTIVE', 'SCROLLBAR_BG_HOVER'] + ['HIGHLIGHT_BG', 'HIGHLIGHT_FG'] + ['SELECTED_BG', 'SELECTED_FG'] + ['SHADOW', 'SHADOW_FOCUS', 'SHADOW_INSET', 'SHADOW_SUBTLE']

        # === Layout ===
        self.root_layout = QVBoxLayout(self)
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget(objectName="tabs")
        self.tabs.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tab_general = QWidget(objectName="general")
        self.tab_general.setLayout(
            self.create_color_picker_layout(self.theme_general))
        self.tab_decks = QWidget(objectName="decks")
        self.tab_decks.setLayout(
            self.create_color_picker_layout(self.theme_decks))
        self.tab_browse = QWidget(objectName="browse")
        self.tab_browse.setLayout(
            self.create_color_picker_layout(self.theme_browse))
        self.tab_extra = QWidget(objectName="extra")
        self.tab_extra.setLayout(
            self.create_color_picker_layout(self.theme_extra))

        self.tab_settings = QWidget(objectName="settings")
        self.tab_settings_layout = QVBoxLayout(self.tab_settings)
        self.tab_settings_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_settings_layout.setSpacing(0)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_content_widget = QWidget()
        settings_bg = self.tab_settings.palette().color(QPalette.ColorRole.Window)
        self.settings_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.settings_scroll.viewport().setAutoFillBackground(True)
        viewport_palette = self.settings_scroll.viewport().palette()
        viewport_palette.setColor(QPalette.ColorRole.Window, settings_bg)
        viewport_palette.setColor(QPalette.ColorRole.Base, settings_bg)
        self.settings_scroll.viewport().setPalette(viewport_palette)
        self.settings_content_widget.setAutoFillBackground(True)
        content_palette = self.settings_content_widget.palette()
        content_palette.setColor(QPalette.ColorRole.Window, settings_bg)
        content_palette.setColor(QPalette.ColorRole.Base, settings_bg)
        self.settings_content_widget.setPalette(content_palette)
        self.settings_layout = QFormLayout(self.settings_content_widget)
        self.settings_layout.setContentsMargins(12, 8, 12, 8)
        self.settings_layout.setVerticalSpacing(10)
        self.theme_label = QLabel(self.texts.get("theme_preset_label", "Theme Preset:"))
        self.theme_label.setStyleSheet(
            'QLabel { font-size: 14px; font-weight: bold }')
        self.settings_layout.addRow(self.theme_label)
        self.theme_buttons_group = QButtonGroup(self)
        self.theme_buttons_group.setExclusive(True)
        self.theme_buttons = {}
        self.theme_preview_icon_labels = {}
        self.theme_buttons_widget = QWidget()
        self.theme_buttons_layout = QVBoxLayout(self.theme_buttons_widget)
        self.theme_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.theme_buttons_layout.setSpacing(6)
        self.theme_buttons_widget.setStyleSheet(
            """
            QPushButton#themePreviewButton {
                background-color: rgba(127, 127, 127, 0.10);
                border: 1px solid rgba(127, 127, 127, 0.32);
                border-radius: 10px;
                min-height: 64px;
                padding: 0;
            }
            QPushButton#themePreviewButton:hover {
                background-color: rgba(127, 127, 127, 0.16);
                border: 1px solid rgba(127, 127, 127, 0.55);
            }
            QPushButton#themePreviewButton:checked {
                background-color: rgba(59, 130, 246, 0.18);
                border: 1px solid #3B82F6;
            }
            QLabel#themePreviewTitle {
                font-size: 14px;
                font-weight: 700;
                color: palette(text);
            }
            QLabel#themePreviewDescription {
                font-size: 13px;
                font-weight: 400;
                color: palette(window-text);
            }
            """
        )
        primary_theme = "Anki" if "Anki" in self.available_themes else self.available_themes[0]
        other_themes = [theme for theme in self.available_themes if theme != primary_theme]

        primary_button = self.create_theme_preview_button(primary_theme)
        self.theme_buttons_layout.addWidget(primary_button)

        other_themes_grid = QGridLayout()
        other_themes_grid.setContentsMargins(0, 0, 0, 0)
        other_themes_grid.setHorizontalSpacing(6)
        other_themes_grid.setVerticalSpacing(6)
        other_themes_grid.setColumnStretch(0, 1)
        other_themes_grid.setColumnStretch(1, 1)
        for idx, theme_name in enumerate(other_themes):
            button = self.create_theme_preview_button(theme_name)
            row = idx // 2
            col = idx % 2
            other_themes_grid.addWidget(button, row, col)
        self.theme_buttons_layout.addLayout(other_themes_grid)
        self.settings_layout.addRow(self.theme_buttons_widget)
        theme_to_font_gap = QWidget()
        theme_to_font_gap.setFixedHeight(14)
        self.settings_layout.addRow(theme_to_font_gap)

        self.enable_font_customization = QCheckBox(
            self.texts.get("enable_font_customization", "Enable font customization")
        )
        self.enable_font_customization.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.enable_font_customization.setChecked(
            bool(self.current_config.get("font_customization_enabled", False))
        )
        self.enable_font_customization.stateChanged.connect(
            lambda _: self.update_font_customization_state()
        )
        self.settings_layout.addRow(self.enable_font_customization)

        self.font_label = QLabel(self.texts["font_label"])
        self.font_label.setStyleSheet(
            'QLabel { font-size: 14px; font-weight: bold }')
        self.settings_layout.addRow(self.font_label)
        self.interface_font = QFontComboBox()
        self.interface_font.setFixedWidth(200)
        self.interface_font.setCurrentFont(QFont(self.current_config["font"]))
        self.settings_layout.addRow(self.interface_font)

        self.font_size = QSpinBox()
        self.font_size.setFixedWidth(200)
        self.font_size.setValue(self.current_config["font_size"])
        self.font_size.setSuffix("px")
        self.settings_layout.addRow(self.font_size)
        self.update_font_customization_state()

        self.settings_scroll.setWidget(self.settings_content_widget)
        self.tab_settings_layout.addWidget(self.settings_scroll)

        self.tabs.resize(300, 200)
        self.tabs.addTab(self.tab_settings, self.texts["settings_tab"])
        self.tabs.addTab(self.tab_general, self.texts["general_tab"])
        self.tabs.addTab(self.tab_decks, self.texts["decks_tab"])
        self.tabs.addTab(self.tab_browse, self.texts["browse_tab"])
        self.tabs.addTab(self.tab_extra, "Extra")
        self.layout.addWidget(self.tabs)

        self.root_layout.addLayout(self.layout)
        self.root_layout.addLayout(self.make_button_box())
        self.setLayout(self.root_layout)
        self.show()

    def update(self) -> None:
        self.reload_theme()

    def reload_theme(self) -> None:
        global themes_parsed
        themes_parsed = get_theme(self.theme_name)
        self.theme_colors = themes_parsed.get("colors")
        self.refresh_color_inputs()
        self.refresh_theme_preview_icons()

    def refresh_color_inputs(self) -> None:
        for update in self.updates:
            update()

    def on_theme_changed(self, theme_name: str) -> None:
        self.theme_name = normalize_theme_name(theme_name)
        button = self.theme_buttons.get(self.theme_name)
        if button and not button.isChecked():
            button.setChecked(True)
        self.reload_theme()

    def update_font_customization_state(self) -> None:
        enabled = self.enable_font_customization.isChecked()
        self.font_label.setEnabled(enabled)
        self.interface_font.setEnabled(enabled)
        self.font_size.setEnabled(enabled)

    def create_theme_preview_button(self, theme_name: str) -> QPushButton:
        button = QPushButton(objectName="themePreviewButton")
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setMinimumHeight(64)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        content_layout = QHBoxLayout(button)
        content_layout.setContentsMargins(10, 4, 10, 4)
        content_layout.setSpacing(10)

        preview = self.build_theme_preview_icon(theme_name).pixmap(92, 56)
        icon_label = QLabel()
        icon_label.setFixedSize(92, 56)
        icon_label.setPixmap(preview)
        icon_label.setScaledContents(False)
        self.theme_preview_icon_labels[theme_name] = icon_label

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        title_label = QLabel(theme_name, objectName="themePreviewTitle")
        description_label = QLabel(
            THEME_PREVIEW_TAGLINES.get(theme_name, "Balanced study palette"),
            objectName="themePreviewDescription",
        )
        description_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)
        text_widget = QWidget()
        text_widget.setLayout(text_layout)

        content_layout.addWidget(icon_label)
        content_layout.addWidget(text_widget, 1)
        content_layout.setAlignment(icon_label, Qt.AlignmentFlag.AlignVCenter)
        content_layout.setAlignment(text_widget, Qt.AlignmentFlag.AlignVCenter)

        idx = len(self.theme_buttons)
        self.theme_buttons_group.addButton(button, idx)
        self.theme_buttons[theme_name] = button
        if theme_name == self.theme_name:
            button.setChecked(True)
        button.clicked.connect(lambda _, t=theme_name: self.on_theme_changed(t))
        return button

    def get_theme_preview_color(self, theme_colors: dict, keys, mode: int, fallback: str) -> QColor:
        for key in keys:
            color_data = theme_colors.get(key)
            if not color_data or len(color_data) <= mode:
                continue
            color = QColor(color_data[mode])
            if color.isValid():
                return color
        fallback_color = QColor(fallback)
        if fallback_color.isValid():
            return fallback_color
        return QColor("#808080")

    def build_theme_preview_icon(self, theme_name: str) -> QIcon:
        theme_preview = get_theme(theme_name)
        theme_colors = theme_preview.get("colors", {})
        preview_mode = get_effective_color_mode()

        canvas = self.get_theme_preview_color(theme_colors, ("CANVAS", "WINDOW_BG"), preview_mode, "#f5f5f5")
        surface = self.get_theme_preview_color(theme_colors, ("CANVAS_ELEVATED", "FRAME_BG"), preview_mode, "#ffffff")
        border = self.get_theme_preview_color(theme_colors, ("BORDER", "MEDIUM_BORDER"), preview_mode, "#c4c4c4")
        fg = self.get_theme_preview_color(theme_colors, ("FG", "TEXT_FG"), preview_mode, "#111827")
        subtle_fg = self.get_theme_preview_color(theme_colors, ("FG_SUBTLE", "FG_FAINT", "SLIGHTLY_GREY_TEXT"), preview_mode, "#6b7280")
        primary = self.get_theme_preview_color(theme_colors, ("BUTTON_PRIMARY_BG", "BUTTON_FOCUS_BG"), preview_mode, "#3b82f6")
        highlight = self.get_theme_preview_color(theme_colors, ("HIGHLIGHT_BG", "SELECTED_BG"), preview_mode, "#dbeafe")

        pixmap = QPixmap(92, 56)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(QPen(border, 1))
        painter.setBrush(canvas)
        painter.drawRoundedRect(QRectF(1, 1, 90, 54), 8, 8)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(surface)
        painter.drawRoundedRect(QRectF(6, 6, 80, 44), 6, 6)

        painter.setBrush(highlight)
        painter.drawRoundedRect(QRectF(11, 12, 40, 6), 3, 3)
        painter.drawRoundedRect(QRectF(11, 22, 26, 5), 2.5, 2.5)

        painter.setBrush(primary)
        painter.drawRoundedRect(QRectF(58, 12, 22, 10), 4, 4)
        painter.drawRoundedRect(QRectF(58, 27, 22, 17), 4, 4)

        painter.setPen(QPen(fg, 1.2))
        painter.drawLine(QPointF(11, 35), QPointF(44, 35))
        painter.setPen(QPen(subtle_fg, 1.2))
        painter.drawLine(QPointF(11, 41), QPointF(39, 41))
        painter.end()

        return QIcon(pixmap)

    def refresh_theme_preview_icons(self) -> None:
        for theme_name, icon_label in self.theme_preview_icon_labels.items():
            icon_label.setPixmap(self.build_theme_preview_icon(theme_name).pixmap(92, 56))

    # === Color Picker Widgets ===
    def color_input(self, key: str) -> QWidget:
        field = QWidget()
        field_layout = QHBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)

        button = QPushButton()
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setFixedWidth(28)
        button.setFixedHeight(28)
        button.setToolTip(self.theme_colors.get(key)[1])

        value = QLabel()
        value.setMinimumWidth(86)

        field_layout.addWidget(button)
        field_layout.addWidget(value)
        field_layout.addStretch(1)

        color_dialog = QColorDialog(self)

        def set_color(rgb: str) -> None:
            color = QColor(rgb)
            if not color.isValid():
                value.setText(str(rgb) if rgb else "invalid")
                button.setStyleSheet(
                    'QPushButton{ background-color: "#f3f4f6"; border: 1px solid #9aa3b2; border-radius: 6px }'
                )
                return

            hex_rgb = color.name(QColor.NameFormat.HexRgb).upper()
            color_dialog.setCurrentColor(color)
            value.setText(hex_rgb)
            button.setStyleSheet(
                'QPushButton{ background-color: "%s"; border: 1px solid #9aa3b2; border-radius: 6px }' % hex_rgb
            )

        def update() -> None:
            try:
                rgb = self.theme_colors.get(key)[color_mode]
            except:
                rgb = "#ff0000"
            set_color(rgb)

        def save(color: QColor) -> None:
            rgb = color.name(QColor.NameFormat.HexRgb)
            self.theme_colors[key][color_mode] = rgb
            set_color(rgb)

        self.updates.append(update)
        update()
        color_dialog.colorSelected.connect(lambda color: save(color))
        button.clicked.connect(lambda _: color_dialog.exec())
        return field

    def create_color_picker_layout(self, colors) -> QLayout:
        layout = QFormLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(10)
        for key in colors:
            label = QLabel(self.theme_colors.get(key)[0])
            layout.addRow(label, self.color_input(key))

        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addLayout(layout)
        wrapper.addStretch(1)
        return wrapper

    def theme_file_editor(self) -> None:
        diag = AnkiRedesignThemeEditor(self, self.theme_name)
        diag.show()

    # === Reset Handling ===
    def reset_colors(self) -> None:
        popup = QMessageBox()
        popup.setIcon(QMessageBox.Icon.Warning)
        popup.setText(f"{self.texts['reset_colors_message']} ({self.theme_name})")
        popup.setWindowTitle(self.texts["reset_colors_window_title"])
        popup.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if popup.exec() != QMessageBox.StandardButton.Yes:
            return
        global themes_parsed
        themes_parsed = get_system_theme(self.theme_name)
        self.theme_colors = themes_parsed.get("colors")
        self.refresh_color_inputs()
        showInfo(self.texts["reset_colors_notice"])

    # === Buttons ===
    def make_button_box(self) -> QWidget:
        def advanced():
            button = QPushButton(self.texts["advanced_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            qconnect(button.clicked, self.theme_file_editor)
            return button

        def reset_colors():
            button = QPushButton(self.texts["reset_colors_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            qconnect(button.clicked, self.reset_colors)
            return button

        def cancel():
            button = QPushButton(self.texts["cancel_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            qconnect(button.clicked, self.accept)
            return button

        def save():
            button = QPushButton(self.texts["save_button"])
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            button.setDefault(True)
            button.setShortcut("Ctrl+Return")
            button.clicked.connect(lambda _: self.save())
            return button

        button_box = QHBoxLayout()
        button_box.addWidget(advanced())
        button_box.addWidget(reset_colors())

        button_box.addStretch()
        button_box.addWidget(cancel())
        button_box.addWidget(save())
        return button_box

    def make_size_policy(self) -> QSizePolicy:
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        return size_policy

    # === Persist Settings ===
    def save(self) -> None:
        global config, color_mode
        config["font_customization_enabled"] = self.enable_font_customization.isChecked()
        config["font"] = self.interface_font.currentFont().family()
        config["font_size"] = self.font_size.value()
        config["theme_name"] = normalize_theme_name(self.theme_name)
        write_config(config)
        config = get_config()
        logger.debug(config)

        color_mode = get_effective_color_mode()
        themes_parsed["colors"] = self.theme_colors
        write_theme(ensure_user_theme(config["theme_name"]), themes_parsed)
        update_theme()

        showInfo(self.texts["changes_message"])
        self.accept()
# === Theme Application Utilities ===

# === Palette Helpers ===
def check_legacy_colors() -> None:
    try:
        _ = colors.items()
    except:
        return False
    return True


# === UI Refresh ===
def refresh_all_windows() -> None:
    # Redraw top toolbar
    mw.toolbar.draw()
    if attribute_exists(gui_hooks, "top_toolbar_did_init_links"):
        gui_hooks.top_toolbar_did_init_links.append(lambda a, b: [redraw_toolbar_legacy(a, b), gui_hooks.top_toolbar_did_init_links.remove(print)])

    # Redraw main body
    if mw.state == "review":
        mw.reviewer._initWeb()
        # Legacy check
        if getattr(mw.reviewer, "_redraw_current_card", False):
            mw.reviewer._redraw_current_card()
            mw.fade_in_webview()
    elif mw.state == "overview":
        mw.overview.refresh()
    elif mw.state == "deckBrowser":
        mw.deckBrowser.show()

    # Redraw toolbar
    if attribute_exists(gui_hooks, "top_toolbar_did_init_links"):
        gui_hooks.top_toolbar_did_init_links.remove(redraw_toolbar)


# === Theme Application ===
def update_theme() -> None:
    global themes_parsed, color_mode
    config_data = get_config()
    theme_name = get_active_theme_name(config_data)
    themes_parsed = get_theme(theme_name)
    theme_colors = themes_parsed.get("colors")
    light = LIGHT_COLOR_MODE
    dark = DARK_COLOR_MODE
    color_mode = get_effective_color_mode()
    day_mode = light
    night_mode = dark
    # Apply theme on colors
    ncolors = {}
    # Legacy color check
    # logger.debug(dir(colors))
    legacy = check_legacy_colors()
    for color_name in theme_colors:
        c = theme_colors.get(color_name)
        ncolors[color_name] = c[color_mode]
        if legacy:
            colors[f"day{c[3].replace('--','-')}"] = c[day_mode]
            colors[f"night{c[3].replace('--','-')}"] = c[night_mode]
        else:
            if getattr(colors, color_name, False):
                if pointVersion() >= 56:
                    setattr(colors, color_name, {"light": c[day_mode], "dark": c[night_mode]})
                else:
                    setattr(colors, color_name, (c[day_mode], c[night_mode]))
    apply_theme(ncolors)
    gui_hooks.debug_console_will_show(mw)
    refresh_all_windows()


# === Palette Application ===
def apply_theme(colors) -> None:
    logger.debug(colors)
    if getattr(theme_manager, "_default_style", False):
        mw.app.setStyle(QStyleFactory.create(theme_manager._default_style))
        if getattr(theme_manager, "default_palette", False):
            mw.app.setPalette(theme_manager.default_palette)
        else:
            theme_manager._apply_palette(mw.app)
    palette = QPalette()
    if pointVersion() >= 56:
        text = QColor(colors["FG"])
        palette.setColor(QPalette.ColorRole.WindowText, text)
        palette.setColor(QPalette.ColorRole.ToolTipText, text)
        palette.setColor(QPalette.ColorRole.Text, text)
        palette.setColor(QPalette.ColorRole.ButtonText, text)

        hlbg = QColor(colors["HIGHLIGHT_BG"])
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["HIGHLIGHT_FG"]))
        palette.setColor(QPalette.ColorRole.Highlight, hlbg)

        canvas = QColor(colors["CANVAS"])
        palette.setColor(QPalette.ColorRole.Window, canvas)
        palette.setColor(QPalette.ColorRole.AlternateBase, canvas)

        palette.setColor(QPalette.ColorRole.Button, QColor(colors["BUTTON_BG"]))

        input_base = QColor(colors["CANVAS_CODE"])
        palette.setColor(QPalette.ColorRole.Base, input_base)
        palette.setColor(QPalette.ColorRole.ToolTipBase, input_base)

        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(colors["FG_SUBTLE"]))

        disabled_color = QColor(colors["FG_DISABLED"])
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, disabled_color)
        palette.setColor(QPalette.ColorRole.Link, QColor(colors["FG_LINK"]))
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)

        # Update webview background
        AnkiWebView._getWindowColor = lambda *args: QColor(colors["CANVAS"])
        AnkiWebView.get_window_bg_color = lambda *args: QColor(colors["CANVAS"])

        theme_manager._apply_palette(mw.app)  # Update palette theme_manager
        mw.app.setPalette(palette)  # Overwrite palette
        theme_manager._apply_style(mw.app)  # Update stylesheet theme_manager
    else:
        color_map = {
            QPalette.ColorRole.Window: "WINDOW_BG",
            QPalette.ColorRole.WindowText: "TEXT_FG",
            QPalette.ColorRole.Base: "FRAME_BG",
            QPalette.ColorRole.AlternateBase: "WINDOW_BG",
            QPalette.ColorRole.ToolTipBase: "TOOLTIP_BG",
            QPalette.ColorRole.ToolTipText: "TEXT_FG",
            QPalette.ColorRole.Text: "TEXT_FG",
            QPalette.ColorRole.Button: "BUTTON_BG",
            QPalette.ColorRole.ButtonText: "TEXT_FG",
            QPalette.ColorRole.BrightText: "HIGHLIGHT_FG",
            QPalette.ColorRole.HighlightedText: "HIGHLIGHT_FG",
            QPalette.ColorRole.Link: "LINK",
            QPalette.ColorRole.NoRole: "WINDOW_BG",
        }
        for color_role in color_map:
            palette.setColor(color_role, QColor(colors[color_map[color_role]]))

        highlight_bg = QColor(colors["HIGHLIGHT_BG"])
        highlight_bg.setAlpha(64)
        palette.setColor(QPalette.ColorRole.Highlight, highlight_bg)

        disabled_color = QColor(colors["DISABLED"])
        palette.setColor(QPalette.ColorRole.PlaceholderText, disabled_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, disabled_color)

        # Update webview background
        AnkiWebView._getWindowColor = lambda *args: QColor(colors["WINDOW_BG"])
        AnkiWebView.get_window_bg_color = lambda *args: QColor(colors["WINDOW_BG"])

        theme_manager._apply_palette(mw.app)  # Update palette theme_manager
        mw.app.setPalette(palette)  # Overwrite palette
        theme_manager._apply_style(mw.app)  # Update stylesheet theme_manager


# === Menu Wiring ===
def create_menu_action(parent: QWidget, dialog_class: QDialog, dialog_name: str) -> QAction:
    def open_dialog():
        dialog = dialog_class(mw)
        return dialog.exec()

    action = QAction(dialog_name, parent)
    action.triggered.connect(open_dialog)
    return action


# === Menu Registration ===
if not hasattr(mw, 'anki_redesign'):
    mw.form.menuTools.addAction(create_menu_action(mw, AnkiRedesignConfigDialog, "Anki Redesign+"))
    mw.reset()
    update_theme()
    if 'Qt6' in QPalette.ColorRole.__module__:
        logger.debug('QT6 detected...')
        mw.reset()
        update_theme()


# === Theme Change Hook ===
def on_theme_did_change() -> None:
    global color_mode
    color_mode = get_effective_color_mode()
    logger.debug("Theme changed")
    mw.reset()
    update_theme()


if attribute_exists(gui_hooks, "theme_did_change"):
    gui_hooks.theme_did_change.append(on_theme_did_change)
