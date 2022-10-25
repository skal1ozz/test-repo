""" Notification object """
from dataclasses import dataclass, field
from typing import Optional

import marshmallow.validate

from entities.json.camel_case_mixin import CamelCaseMixin, timestamp_factory


@dataclass
class NotificationUrl(CamelCaseMixin):
    """ Notifiction URL """
    title: Optional[str]
    link: Optional[str]


@dataclass
class Notification(CamelCaseMixin):
    """ Notification Dataclass """
    message_id: Optional[str]
    destination: str
    subject: Optional[str] = field(default=None)
    message: Optional[str] = field(default=None)
    title: Optional[str] = field(default=None)
    url: Optional[NotificationUrl] = field(default_factory=NotificationUrl)
    acknowledge: Optional[bool] = field(default=False)
    tenant_id: Optional[str] = field(default=None)

    def to_db(self) -> "NotificationCosmos":
        """ Create NotificationCosmos """
        return NotificationCosmos(message_id=self.message_id,
                                  destination=self.destination,
                                  subject=self.subject,
                                  message=self.message,
                                  title=self.title,
                                  url=self.url,
                                  acknowledge=self.acknowledge,
                                  tenant_id=self.tenant_id)


# noinspection PyDataclass
@dataclass
class NotificationCosmos(Notification):
    """ Notification Dataclass """
    # We have to add these fields
    id: Optional[str] = field(default=None)
    timestamp: Optional[int] = field(default_factory=timestamp_factory)
