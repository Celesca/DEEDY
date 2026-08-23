import json
import os
import contextvars

# Create a context variable for the locale with default 'zh'
_locale_ctx_var = contextvars.ContextVar('locale', default='zh')

_locales_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'locales')

# Load language registry
with open(os.path.join(_locales_dir, 'languages.json'), 'r', encoding='utf-8') as f:
    _languages = json.load(f)

# Load translation files
_translations = {}
for filename in os.listdir(_locales_dir):
    if filename.endswith('.json') and filename != 'languages.json':
        locale_name = filename[:-5]
        with open(os.path.join(_locales_dir, filename), 'r', encoding='utf-8') as f:
            _translations[locale_name] = json.load(f)


def set_locale(locale: str):
    """Set locale for current context/thread."""
    _locale_ctx_var.set(locale)


def get_locale() -> str:
    raw = _locale_ctx_var.get()
    return raw if raw in _translations else 'zh'

def get_locale_from_header(accept_language: str) -> str:
    """Helper to extract locale from Accept-Language header"""
    if not accept_language:
        return 'zh'
    primary = accept_language.split(',')[0].split(';')[0].strip()
    if primary in _translations:
        return primary
    short = primary.split('-')[0]
    if short in _translations:
        return short
    return 'zh'

def t(key: str, **kwargs) -> str:
    locale = get_locale()
    messages = _translations.get(locale, _translations.get('zh', {}))

    value = messages
    for part in key.split('.'):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break

    if value is None:
        value = _translations.get('zh', {})
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

    if value is None:
        return key

    if kwargs:
        for k, v in kwargs.items():
            value = value.replace(f'{{{k}}}', str(v))

    return value


def get_language_instruction() -> str:
    locale = get_locale()
    lang_config = _languages.get(locale, _languages.get('zh', {}))
    return lang_config.get('llmInstruction', '请使用中文回答。')
