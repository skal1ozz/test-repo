""" PA message to send to Teams """
from dataclasses import dataclass
from typing import Optional

from entities.json.camel_case_mixin import CamelCaseMixin


@dataclass
class PAMessage(CamelCaseMixin):
    """ PA message Schema """
    conversation_id: str
    tenant_id: str
    text: Optional[str]
    card: Optional[str]
