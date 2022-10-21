""" Notification Schema Implementation """
import marshmallow_dataclass

from entities.json.camel_case_schema import CamelCaseSchema


@marshmallow_dataclass.dataclass(base_schema=CamelCaseSchema)
class AdminUser:
    """ Notification Schema """
    login: str
    password: str
