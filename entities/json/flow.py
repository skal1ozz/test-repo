""" Flow object """
from dataclasses import dataclass, field
from typing import Optional


from entities.json.camel_case_mixin import CamelCaseMixin


@dataclass
class Flow(CamelCaseMixin):
    """ Notification Dataclass """
    tenant_id: str
    cmd: str
    url: str
