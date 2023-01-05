""" PA message to send to Teams """
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict

from entities.json.camel_case_mixin import CamelCaseMixin


@dataclass
class PAMessage(CamelCaseMixin):
    """ PA message Schema """
    conversation_id: str
    tenant_id: str
    text: Optional[str] = None
    card: Optional[Dict] = None
    cards: Optional[List[Dict]] = field(default_factory=list)
