""" Conversation Reference Implementation """
from typing import Dict

from botbuilder.schema import ConversationReference, ConversationAccount, \
    ChannelAccount
from marshmallow import fields, EXCLUDE, validate, post_load

from .camel_case_schema import CamelCaseSchema


class UserSchema(CamelCaseSchema):
    """ User Schema """
    id = fields.String(required=True)
    name = fields.String(required=True)
    # may be null if it's a bot
    aad_object_id = fields.String(required=True, allow_none=True)
    role = fields.String(required=True, allow_none=True)


class ConversationSchema(CamelCaseSchema):
    """ Conversation Schema """
    is_group = fields.Boolean(required=True, allow_none=True)
    conversation_type = fields.String(required=True)
    id = fields.String(required=True)
    name = fields.String(required=True, allow_none=True)
    aad_object_id = fields.String(required=True, allow_none=True)
    role = fields.String(required=True, allow_none=True)
    tenant_id = fields.String(required=True)
    # Microsoft does not describe this object at all
    properties = fields.Dict(required=False, allow_none=True)


class ConversationReferenceSchema(CamelCaseSchema):
    """ Conversation Reference schema """

    activity_id = fields.String()
    user = fields.Nested(UserSchema, required=False, unknown=EXCLUDE)
    bot = fields.Nested(UserSchema, unknown=EXCLUDE)
    conversation = fields.Nested(ConversationSchema, unknown=EXCLUDE)
    channel_id = fields.String(required=True)
    locale = fields.String(required=True)
    service_url = fields.String()

    @post_load
    def create_conversation_reference(self, data, **_kwargs):
        """ Create Conversation Reference """
        data.update(dict(
            user=ChannelAccount(**data.pop("user")),
            bot=ChannelAccount(**data.pop("bot")),
            conversation=ConversationAccount(**data.pop("conversation"))
        ))
        return ConversationReference(**data)
