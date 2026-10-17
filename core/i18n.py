from core.locales import en, ru, uz

LANGUAGES = {
    'uz': ("🇺🇿 O'zbekcha", uz.TEXTS),
    'ru': ('🇷🇺 Русский', ru.TEXTS),
    'en': ('🇬🇧 English', en.TEXTS),
}
DEFAULT_LANGUAGE = 'uz'


def t(key: str, lang: str | None = None, **kwargs) -> str:
    texts = LANGUAGES.get(lang or DEFAULT_LANGUAGE, LANGUAGES[DEFAULT_LANGUAGE])[1]
    # Fall back to Uzbek, then to the key itself, so a missing translation never breaks a handler
    text = texts.get(key) or LANGUAGES[DEFAULT_LANGUAGE][1].get(key, key)
    return text.format(**kwargs) if kwargs else text


def all_languages(key: str) -> set[str]:
    """The same text in every language, to match reply keyboard buttons whatever language the user picked."""
    return {texts[key] for _, texts in LANGUAGES.values() if key in texts}
