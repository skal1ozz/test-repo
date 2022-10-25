""" Notification object """
from dataclasses import dataclass, field
from typing import Optional

from entities.json.camel_case_mixin import CamelCaseMixin


class MXTypes:
    """ MedX Types """
    UNKNOWN = "UNKNOWN"
    ACKNOWLEDGE = "acknowledge"

    class Task:
        """ Task types """
        DEFAULT = "task/default"
        NOTIFICATION = "task/notification"


@dataclass
class MedX(CamelCaseMixin):
    """ MedX data """
    type: str
    notification_id: Optional[str]
    tenant_id: Optional[str]
