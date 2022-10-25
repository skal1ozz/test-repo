""" Notification Schema Implementation """
from marshmallow import fields

from .camel_case_schema import CamelCaseSchema


class AcknowledgeSchema(CamelCaseSchema):
    """ Notification Schema """
    id = fields.String(required=True, allow_none=True)  # database message id
    notification_id = fields.String(required=True)
    tenant_id = fields.String(required=True)
    username = fields.String(required=True)
    user_aad_id = fields.String(required=True)
    timestamp = fields.Integer(required=True)
