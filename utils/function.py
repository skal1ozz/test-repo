""" Handy Functions """
from typing import List, Optional, Dict


def get_first_or_none(items: List) -> Optional[Dict[str, any]]:
    """ Get first object from list or return None len < 1 """
    if len(items) > 0:
        return items[0]
    return None
