""" Message extension bot """
import asyncio
import uuid
from asyncio import Future
from typing import Optional
from urllib.parse import urlparse, parse_qsl, urlencode

from aiohttp.web_app import Application
from botbuilder.core import (TurnContext, CardFactory, BotFrameworkAdapter,
                             BotFrameworkAdapterSettings)
from botbuilder.schema import Activity, ActivityTypes, ConversationReference
from botbuilder.schema.teams import (TaskModuleContinueResponse,
                                     TaskModuleTaskInfo, TaskModuleResponse,
                                     TaskModuleRequest)
from botbuilder.core.teams import TeamsActivityHandler
from marshmallow import EXCLUDE

from bots.exceptions import ConversationNotFound
from config import TaskModuleConfig, AppConfig
from entities.json.conversation_reference_schema import (
    ConversationReferenceSchema
)
from entities.json.medx import MedX, MXTypes
from entities.json.notification import NotificationCosmos
from utils.card_helper import CardHelper
from utils.cosmos_client import CosmosClient, ItemNotFound
from utils.function import get_first_or_none


class TeamsMessagingExtensionsActionPreviewBot(TeamsActivityHandler):
    """ The Bot """

    settings: BotFrameworkAdapterSettings
    adapter: BotFrameworkAdapter
    app: Application
    cosmos_client: CosmosClient

    def __init__(self, settings: BotFrameworkAdapterSettings,
                 adapter: BotFrameworkAdapter):
        self.settings = settings
        self.adapter = adapter

    def add_web_app(self, app):
        """ Add web app instance """
        self.app = app

    def add_cosmos_client(self, cosmos_client: CosmosClient):
        """ Add cosmos client to the bot """
        self.cosmos_client = cosmos_client

    def add_adapter(self, adapter):
        """ Add bot adapter instance """
        self.adapter = adapter

    @staticmethod
    def get_mx(turn_context: TurnContext) -> Optional[MedX]:
        """ Get Medx data """
        if isinstance(turn_context.activity.value, dict):
            mx = turn_context.activity.value.get("mx", {})
            return MedX.get_schema(unknown=EXCLUDE).load(mx)

    @staticmethod
    def get_mx_type(turn_context: TurnContext) -> Optional[str]:
        """ Get message MX type or None """
        # "mx": {
        #     "type": "task/notification",
        #     "notificationId": notification_id
        # }
        if isinstance(turn_context.activity.value, dict):
            mx = turn_context.activity.value.get("mx", {})
            return mx.get("type", None)

    @staticmethod
    def get_mx_notification_id(turn_context: TurnContext) -> Optional[str]:
        """ Get message MX notification ID or None """
        if isinstance(turn_context.activity.value, dict):
            mx = turn_context.activity.value.get("mx", {})
            return mx.get("notificationId", None)

    def send_notification(self, notification: NotificationCosmos) -> Future[str]:
        """ Notify conversation that there's a message waiting in portal """
        io_loop = asyncio.get_event_loop()
        future = Future()

        # reset parameters
        notification.id = uuid.uuid4().__str__()
        notification.tenant_id = AppConfig.TENANT_ID

        async def routine():
            """ async routine """
            try:
                reference = await self.cosmos_client.get_conversation(
                    notification.destination
                )
            except ItemNotFound:
                future.set_exception(ConversationNotFound("not found"))
                return
            except Exception as e:
                future.set_exception(e)
                return

            async def callback(turn_context: TurnContext) -> None:
                """ Turn Context callback. Kinda awful syntax, I know """
                # TODO(s1z): Add exception handler
                #            (like conversation not found etc...)
                try:
                    card = CardHelper.create_notification_card(
                        await self.cosmos_client.create_notification(
                            notification
                        )
                    )
                    attachments = [CardFactory.adaptive_card(card)]
                    message = Activity(type=ActivityTypes.message,
                                       attachments=attachments)
                    await turn_context.send_activity(message)
                    future.set_result(notification.id)
                except Exception as e:
                    future.set_exception(e)

            await self.adapter.continue_conversation(reference, callback,
                                                     self.settings.app_id)
        io_loop.create_task(routine())
        return future

    @staticmethod
    def generate_url(url: str, channel_id: str) -> str:
        """ Generate URL for the task module """
        parsed_url = urlparse(url)
        params = dict(parse_qsl(parsed_url.query))
        params.update(dict(channelId=channel_id))
        # noinspection PyProtectedMember
        return parsed_url._replace(query=urlencode(params)).geturl()

    async def on_conversation_update_activity(self, turn_context: TurnContext):
        """ On update conversation """
        print("activity:", turn_context.activity)
        await self.cosmos_client.create_conversation_reference(turn_context)

    async def handle_submit_action(self, turn_context: TurnContext) -> None:
        """ Handle card submit action """
        mx = self.get_mx(turn_context)
        if mx.type == MXTypes.ACKNOWLEDGE:
            try:
                account = turn_context.activity.from_property
                acks = await self.cosmos_client.get_acknowledge_items(
                    mx.notification_id
                )
                if len(acks) > 0:
                    return

                await self.cosmos_client.create_acknowledge(mx.notification_id,
                                                            account)
                notification = await self.cosmos_client.get_notification(
                    mx.notification_id
                )
                card = CardHelper.create_notification_card(
                    notification,
                    turn_context.activity.from_property.name
                )
                attachments = [CardFactory.adaptive_card(card)]
                message = Activity(id=turn_context.activity.reply_to_id,
                                   type=ActivityTypes.message,
                                   attachments=attachments)
                await turn_context.update_activity(message)
            except ItemNotFound:
                # todo(s1z): Handle unknown notification ID
                pass
            return
        await turn_context.send_activity("Unknown request!")

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """ on message activity """
        if turn_context.activity.value is not None:
            return await self.handle_submit_action(turn_context)

        # try to save conversation reference,
        # who knows maybe we didn't get the on_conversation_update!
        await self.cosmos_client.create_conversation_reference(turn_context)
        card = CardHelper.load_assets_card("default_card")
        attachments = [CardFactory.adaptive_card(card)]
        message = Activity(type=ActivityTypes.message, attachments=attachments)
        await turn_context.send_activity(message)

    async def on_mx_task_unsupported(self, turn_context: TurnContext) \
            -> TaskModuleResponse:
        """ On unsupported request """
        return await self.on_mx_task_default(turn_context)

    async def on_mx_task_notification_url(self, turn_context: TurnContext,
                                          notification_id: str) \
            -> TaskModuleResponse:
        """ On MX Task fetch Notification URL """
        try:
            notification = await self.cosmos_client.get_notification(
                notification_id=notification_id
            )
            link = notification.url.link
            if link is not None:
                task_info = TaskModuleTaskInfo(title=TaskModuleConfig.TITLE,
                                               width=TaskModuleConfig.WIDTH,
                                               height=TaskModuleConfig.HEIGHT,
                                               url=link,
                                               fallback_url=link)
                return TaskModuleResponse(
                    task=TaskModuleContinueResponse(value=task_info)
                )
        except ItemNotFound:
            print(f"item '{notification_id}' not found")
        return await self.on_mx_task_default(turn_context)

    async def on_mx_task_default(self, turn_context: TurnContext) \
            -> TaskModuleResponse:
        """ On MX Task default handler """
        url = self.generate_url(TaskModuleConfig.URL,
                                turn_context.activity.conversation.id)
        task_info = TaskModuleTaskInfo(title=TaskModuleConfig.TITLE,
                                       width=TaskModuleConfig.WIDTH,
                                       height=TaskModuleConfig.HEIGHT,
                                       url=url,
                                       fallback_url=url)
        return TaskModuleResponse(
            task=TaskModuleContinueResponse(value=task_info)
        )

    async def on_teams_task_module_fetch(
            self, turn_context: TurnContext,
            task_module_request: TaskModuleRequest
    ) -> TaskModuleResponse:
        """ On task module fetch.
            Requested when user clicks on "msteams": {"type": "task/fetch"} """
        # "mx": {
        #     "type": "task/notification",
        #     "notificationId": notification_id
        # }
        mx = MedX.get_schema(unknown=EXCLUDE).load(
            task_module_request.data.get("mx", dict())
        )
        if mx.type == MXTypes.Task.NOTIFICATION and mx.notification_id:
            # 1. save action to DB
            # 2. return URL
            initiator = turn_context.activity.from_property.name
            await self.cosmos_client.create_initiation(initiator,
                                                       mx.notification_id)
            return await self.on_mx_task_notification_url(turn_context,
                                                          mx.notification_id)
        return await self.on_mx_task_default(turn_context)
