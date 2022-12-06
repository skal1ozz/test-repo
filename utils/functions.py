""" Handy Functions """
import binascii
import sys
import urllib.parse
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


def get_first_or_none(items: List, default=None) -> Optional[Dict[str, any]]:
    """ Get first object from list or return None len < 1 """
    if len(items) > 0:
        return items[0]
    return default


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
    except (TypeError, binascii.Error, AttributeError):
        return default


def b64encode_str_safe(data: str, encoding="utf-8",
                       default=None) -> Optional[str]:
    """ Safe b64decode_str """
    try:
        return b64encode_str(data, encoding)
    except (TypeError, binascii.Error, AttributeError):
        return default


def quote_b64decode_str_safe(data: str, encoding="utf-8",
                             default=None) -> Optional[str]:
    """ Decode B64 data and then url_decode it """
    data_quoted = b64decode_str_safe(data, encoding, default)
    try:
        return urllib.parse.unquote(data_quoted)
    except TypeError:
        Log.d(TAG, "quote_b64decode_str_safe: error, returning default")
    return default


def quote_b64encode_str_safe(data: str, encoding="utf-8",
                             default=None) -> Optional[str]:
    """ url_encode data end then encode it into b64 """
    try:
        data_quoted = urllib.parse.quote(data)  # str even if input is bytes
    except TypeError:
        Log.d(TAG, "quote_b64encode_str_safe: error, returning default")
        return default
    return b64encode_str_safe(data_quoted, encoding, default)


def b64encode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64encode(data).replace(b"=", b'')


def b64decode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64decode(data + b'===')
