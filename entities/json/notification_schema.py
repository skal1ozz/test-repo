""" Notification Schema Implementation """
from marshmallow import fields, EXCLUDE

from .camel_case_schema import CamelCaseSchema


class NotificationURLSchema(CamelCaseSchema):
    """ Notification URL Schema """
    title = fields.String()
    link = fields.String()


# TODO(s1z): Migrate to marshmallow-dataclass
class NotificationSchema(CamelCaseSchema):
    """ Notification Schema """
    id = fields.String(required=True, allow_none=True)  # database message id
    tenant_id = fields.String(required=True, allow_none=True)
    destination = fields.String(required=True)
    message_id = fields.String()  # teams message id
    subject = fields.String()
    message = fields.String()
    title = fields.String()
    url = fields.Nested(NotificationURLSchema, unknown=EXCLUDE)
    acknowledge = fields.Boolean(default=False)
