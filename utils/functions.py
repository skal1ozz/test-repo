""" Handy Functions """
import binascii
from base64 import b64encode, b64decode
from typing import List, Optional, Dict, Tuple

from botbuilder.core import TurnContext

from utils.log import Log


TAG = __name__


DEFAULT_LOCALE = "en"


def get_locale(turn_context: TurnContext, default=DEFAULT_LOCALE) -> str:
    """ Try to get locale and fallback to "en" """
    reference = TurnContext.get_conversation_reference(turn_context.activity)
    if reference.locale is None:
        Log.w(TAG, "get_locale::Error: locale is None")
    Log.w(TAG, "get_locale: returning default locale")
    return default


def get_i18n(turn_context: TurnContext,
             default: str = DEFAULT_LOCALE,
             fallback: str = DEFAULT_LOCALE):
    """ Get i18n configured """
    from config import STRINGS_PATH
    import i18n
    locale = get_locale(turn_context, default)
    i18n.load_path.append(STRINGS_PATH)
    i18n.set("enable_memoization", True)
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('locale', locale)
    i18n.set('fallback', fallback)
    return i18n


def get_first_or_none(items: List) -> Optional[Dict[str, any]]:
    """ Get first object from list or return None len < 1 """
    if len(items) > 0:
        return items[0]
    return None


def parse_auth_header(header: Optional[str]) -> Tuple[Optional[str],
                                                      Optional[str]]:
    """ Parse Authorization header and return Type, Value or None """
    if isinstance(header, (str, bytes)):
        try:
            t, v = header.split(" ")[:2]
            return t, v
        except ValueError:
            pass
    return None, None


def b64encode_str(data: str, encoding="utf-8") -> str:
    """ Decode base64 str and return decoded string """
    return b64encode_np(data.encode(encoding)).decode(encoding)


def b64decode_str(data: str, encoding="utf-8") -> str:
    """ Decode base64 str and return decoded string """
    return b64decode_np(data.encode(encoding)).decode(encoding)


def b64decode_str_safe(data: str, encoding="utf-8",
                       default=None) -> Optional[str]:
    """ Safe b64decode_str """
    try:
        return b64decode_str(data, encoding)
    except (TypeError, binascii.Error):
        return default


def b64encode_str_safe(data: str, encoding="utf-8",
                       default=None) -> Optional[str]:
    """ Safe b64decode_str """
    try:
        return b64encode_str(data, encoding)
    except (TypeError, binascii.Error):
        return default


def b64encode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64encode(data).replace(b"=", b'')


def b64decode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64decode(data + b'===')
