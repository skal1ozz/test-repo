""" PA message to send to Teams """
from typing import Optional

import marshmallow_dataclass

from entities.json.camel_case_schema import CamelCaseSchema


@marshmallow_dataclass.dataclass(base_schema=CamelCaseSchema)
class PAMessage:
    """ PA message Schema """
    conversation_id: str
    tenant_id: str
    text: Optional[str]
    card: Optional[str]
