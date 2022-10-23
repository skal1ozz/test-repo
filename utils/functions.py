""" Handy Functions """
from base64 import b64encode, b64decode
from typing import List, Optional, Dict


def get_first_or_none(items: List) -> Optional[Dict[str, any]]:
    """ Get first object from list or return None len < 1 """
    if len(items) > 0:
        return items[0]
    return None


def b64encode_str(data: str, encoding="utf-8") -> str:
    """ Decode base64 str and return decoded string """
    return b64encode_np(data.encode(encoding)).decode(encoding)


def b64decode_str(data: str, encoding="utf-8") -> str:
    """ Decode base64 str and return decoded string """
    return b64decode_np(data.encode(encoding)).decode(encoding)


def b64encode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64encode(data).replace(b"=", b'')


def b64decode_np(data: bytes) -> bytes:
    """ B64 without paddings """
    return b64decode(data + b'===')