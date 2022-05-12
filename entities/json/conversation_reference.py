""" Conversation reference object """
from dataclasses import dataclass, field
from typing import Optional, Any, Dict

from botbuilder.schema import (
    ConversationReference as MSConversationReference, ConversationAccount,
    ChannelAccount
)


from entities.json.camel_case_mixin import CamelCaseMixin, timestamp_factory


@dataclass
class Account(CamelCaseMixin):
    """ Account Channel object """
    id: str
    # This is a bullshit, microsoft sends null name!
    name: Optional[str] = field(default=None)
    # may be null if it's a bot
    aad_object_id: Optional[str] = field(default=None)
    role: Optional[str] = field(default=None)


@dataclass
class Conversation(CamelCaseMixin):
    """ Conversation URL """
    id: str
    tenant_id: str
    conversation_type: str = field(default=None)
    is_group: Optional[bool] = field(default=None)
    name: Optional[str] = field(default=None)
    aad_object_id: Optional[str] = field(default=None)
    role: Optional[str] = field(default=None)
    # Microsoft does not describe this object at all
    properties: Optional[Dict[str, Any]] = field(default=None)


@dataclass
class ConversationReference(CamelCaseMixin):
    """ Conversation Reference schema """
    bot: Optional[Account]
    conversation: Conversation
    channel_id: str
    service_url: str
    # has to be not null but MS sends null
    locale: Optional[str] = field(default=None)
    activity_id: Optional[str] = field(default=None)
    user: Optional[Account] = field(default=None)

    def to_ms_reference(self) -> MSConversationReference:
        """ Convert dataclass to microsoft conversation reference object """
        return MSConversationReference(
            activity_id=self.activity_id,
            channel_id=self.channel_id,
            locale=self.locale,
            service_url=self.service_url,
            user=ChannelAccount(
                id=self.user.id,
                name=self.user.name,
                aad_object_id=self.user.aad_object_id,
                role=self.user.role
            ),
            bot=ChannelAccount(
                id=self.bot.id,
                name=self.bot.name,
                aad_object_id=self.bot.aad_object_id,
                role=self.bot.role
            ),
            conversation=ConversationAccount(
                is_group=self.conversation.is_group,
                conversation_type=self.conversation.conversation_type,
                id=self.conversation.id,
                name=self.conversation.name,
                aad_object_id=self.conversation.aad_object_id,
                role=self.conversation.role,
                tenant_id=self.conversation.tenant_id,
                properties=self.conversation.properties
            )
        )
