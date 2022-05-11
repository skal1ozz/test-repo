""" Acknowledge object """
from dataclasses import dataclass, field
from typing import Optional

from entities.json.camel_case_mixin import CamelCaseMixin, uuid_factory


@dataclass
class Acknowledge(CamelCaseMixin):
    """ Acknowledge """
    id: str = field(default_factory=uuid_factory)
    notification_id: Optional[str] = field(default=None)
    username: Optional[str] = field(default=None)
    user_aad_id: Optional[str] = field(default=None)
    timestamp: Optional[int] = field(default=None)
