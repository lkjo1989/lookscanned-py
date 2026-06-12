"""Locale / i18n support for Look Scanned.

Detects system language and provides translation strings for the GUI.
CLI uses English strings by default (not localised).
"""

from __future__ import annotations

import locale
import os
import sys


def _detect_lang() -> str:
    """Detect the system language and return a language code (``en`` or ``zh``).

    Checks, in order:
    1. ``LOOKSCANNED_LANG`` environment variable
    2. ``LANG`` / ``LC_ALL`` / ``LC_MESSAGES`` environment variables
    3. ``locale.getdefaultlocale()``
    4. Defaults to ``en``.
    """
    # Explicit override
    env_lang = os.environ.get("LOOKSCANNED_LANG", "")
    if env_lang:
        return env_lang[:2].lower()

    # POSIX locale env vars
    for var in ("LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "")
        if val:
            return val[:2].lower()

    # locale module
    try:
        default = locale.getdefaultlocale()
        if default and default[0]:
            return default[0][:2].lower()
    except (ValueError, locale.Error):
        pass

    # On Windows, try the Win32 API
    if sys.platform == "win32":
        try:
            import ctypes

            windll = ctypes.windll.kernel32
            lang_id = windll.GetUserDefaultUILanguage()
            primary = lang_id & 0xFF
            if primary == 0x04:  # zh
                return "zh"
        except Exception:
            pass

    return "en"


_current_lang = ""


def get_lang() -> str:
    """Return the current language code (``en`` or ``zh``)."""
    global _current_lang
    if not _current_lang:
        _current_lang = _detect_lang()
    return _current_lang


def set_lang(lang: str) -> None:
    """Override the language code (``en`` or ``zh``)."""
    global _current_lang
    _current_lang = lang[:2].lower()


def tr(key: str, **kwargs: object) -> str:
    """Translate a string key to the current language.

    Args:
        key: Dot-separated key (e.g. ``"settings.rotate"``).
        **kwargs: Format values for placeholders like ``{count}``.

    Returns:
        Translated string, or the key itself if not found.
    """
    lang = get_lang()

    if lang == "zh":
        from .zh import strings as zh_strings

        s = zh_strings.get(key)
    else:
        from .en import strings as en_strings

        s = en_strings.get(key)

    if s is None:
        # Fallback to English for missing keys
        from .en import strings as en_strings

        s = en_strings.get(key, key)

    if kwargs:
        return s.format(**kwargs)
    return s
