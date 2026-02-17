from aqt import mw

DEFAULT_THEME_NAME = "Anki"


def _to_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


# === Config Access ===
def get_config() -> dict:
    raw: dict = mw.addonManager.getConfig(__name__) or dict()
    theme_name = raw.get("theme_name", raw.get("theme", DEFAULT_THEME_NAME))
    if not isinstance(theme_name, str) or not theme_name.strip():
        theme_name = DEFAULT_THEME_NAME
    elif theme_name.endswith(".json"):
        theme_name = theme_name[:-5]
    config = {
        "font": raw.get("font", "Arial"),
        "fallbackFonts": raw.get("fallbackFonts", "sans-serif"),
        "font_size": int(raw.get("font_size", "14")),
        "font_customization_enabled": _to_bool(raw.get("font_customization_enabled", False)),
        "theme_name": theme_name.strip(),
    }
    return config

# === Config Persistence ===
def write_config(config):
    for key in config.keys():
        if not isinstance(config[key], str):
            config[key] = str(config[key])
    mw.addonManager.writeConfig(__name__, config)

# === Module State ===
config = get_config()
