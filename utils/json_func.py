""" JSON helper module """
import sys
from typing import Any, Union, Optional, Mapping, Iterable

import simplejson as json
import simplejson.scanner as json_scanner

from utils.log import Log


TAG = __name__


def json_loads(data: Union[str, bytes], default: Optional[Any] = None) -> \
        Union[Mapping[str, Any], Iterable[Mapping[str, Any]]]:
    """ Json.loads wrapper, tries to load data and prints errors if any """
    try:
        j_data = json.loads(data, strict=False)
        if isinstance(j_data, dict) or isinstance(j_data, list):
            return j_data
    except TypeError:
        Log.e("json_loads", "TypeError:", sys.exc_info())
    except json_scanner.JSONDecodeError:
        Log.e("json_loads", "JSONDecodeError:", sys.exc_info())
    return default


def json_dumps(*args: Any, **kwargs: Mapping[str, Any]) -> str:
    """ Json.dumps wrapper, tries to dump data and prints errors if any """
    try:
        return json.dumps(*args, **kwargs)
    except Exception:
        Log.e("json_loads", "error:", exc_info=sys.exc_info())
        raise
