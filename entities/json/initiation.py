""" Initiation object """
from dataclasses import dataclass, field
from typing import Optional


from entities.json.camel_case_mixin import CamelCaseMixin


@dataclass
class Initiation(CamelCaseMixin):
    """ Notification Dataclass """
    initiator: str  # User name
    notification_id: str  # Notification ID
    timestamp: Optional[int] = field(default=None)
    id: Optional[str] = field(default=None)  # Unique Initiation ID
