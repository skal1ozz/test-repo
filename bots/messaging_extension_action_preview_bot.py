""" Message extension bot """
import asyncio
import sys
import time
import uuid
from asyncio import Future
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qsl, urlencode, unquote

import aiohttp
from aiohttp.web_app import Application
from botbuilder.core import (TurnContext, CardFactory, BotFrameworkAdapter,
                             BotFrameworkAdapterSettings)
from botbuilder.schema import Activity, ActivityTypes, ResourceResponse
from botbuilder.schema.teams import (TaskModuleContinueResponse,
                                     TaskModuleTaskInfo, TaskModuleResponse,
                                     TaskModuleRequest)
from botbuilder.core.teams import TeamsActivityHandler
from botframework.connector import Channels
from marshmallow import EXCLUDE

from bots.exceptions import ConversationNotFound
from config import TaskModuleConfig, AppConfig
from entities.json.medx import MedX, MXTypes
from entities.json.notification import NotificationCosmos
from utils.card_helper import CardHelper
from utils.cosmos_client import CosmosClient, ItemNotFound
from utils.functions import get_i18n
from utils.log import Log


TAG = __name__


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

    def send_message(self,
                     conversation_id: str,
                     tenant_id: str, text: str = None,
                     card: Dict[any, any] = None) -> Future[ResourceResponse]:
        """ Send message as a bot """
        io_loop = asyncio.get_event_loop()
        future = Future()

        async def routine():
            """ async routine """
            try:
                reference = await self.cosmos_client.get_conversation(
                    conversation_id, tenant_id
                )
            except ItemNotFound:
                future.set_exception(ConversationNotFound("not found"))
                return
            except Exception as e:
                future.set_exception(e)
                return

            async def callback(turn_context: TurnContext) -> None:
                """ Turn Context callback. Kinda awful syntax, I know """
                try:
                    attachments = None
                    if card is not None:
                        attachments = [CardFactory.adaptive_card(card)]

                    response = await turn_context.send_activity(Activity(
                        type=ActivityTypes.message,
                        text=text,
                        attachments=attachments)
                    )
                    if response:
                        future.set_result(response)
                except Exception as exception:
                    future.set_exception(exception)

            await self.adapter.continue_conversation(reference, callback,
                                                     self.settings.app_id)
        io_loop.create_task(routine())
        return future

    def send_notification(self, notification: NotificationCosmos)\
            -> Future[str]:
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
                except Exception as exception:
                    future.set_exception(exception)

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
        i18n = get_i18n(turn_context)
        await self.cosmos_client.create_conversation_reference(turn_context)
        if turn_context.activity.channel_id == Channels.ms_teams:
            members = []
            for member in turn_context.activity.members_added:
                if member.id != turn_context.activity.recipient.id:
                    members.append(member)
            if len(members) == 1 and turn_context.activity.members_added:
                member = members[0]
                name = member.name or ''
                bot_name = AppConfig.BOT_NAME
                cmd_help = i18n.t("cmd_help")
                greetings = i18n.t("hi_message", name=name, bot_name=bot_name,
                                   cmd_help=cmd_help)
                await turn_context.send_activity(greetings)
                return
            if len(members) > 1 and turn_context.activity.members_added:
                bot_name = AppConfig.BOT_NAME
                cmd_help = i18n.t("cmd_help")
                greetings = i18n.t("greetings_message", bot_name=bot_name,
                                   cmd_help=cmd_help)
                await turn_context.send_activity(greetings)
                return

    async def handle_submit_action(self, turn_context: TurnContext) -> None:
        """ Handle card submit action """
        i18n = get_i18n(turn_context)

        mx = self.get_mx(turn_context)
        if mx.type == MXTypes.ACKNOWLEDGE:
            try:
                account = turn_context.activity.from_property
                ack_objects = await self.cosmos_client.get_acknowledge_items(
                    mx.notification_id
                )
                if len(ack_objects) > 0:
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
                # DO NOTHING, Notification not found!
                pass
            return
        await turn_context.send_activity(i18n.t("unknown_request"))

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """ Fired when message is received """
        i18n = get_i18n(turn_context)

        # check tenant
        if turn_context.activity.conversation.tenant_id != AppConfig.TENANT_ID:
            await turn_context.send_activity(i18n.t("tenant_forbidden"))
            return

        # save conversation reference
        reference = await self.cosmos_client.create_conversation_reference(
            turn_context
        )

        if turn_context.activity.value is not None:
            return await self.handle_submit_action(turn_context)

        """ DATA STRUCTURE:
            {
                "authorizartion": {
                    "token": "123"
                },
                "message": "message",
                "reference": {
                    "user": {
                        "name": null,
                        "id": "29:12v6wyPB....",
                        "role": null,
                        "aadObjectId": "ed77c873-f9a4-4d94-bd08-e159fa3349d2"
                    },
                    "channelId": "msteams",
                    "conversation": {
                        "id": "a:1aStwF-.....jogUhlEo",
                        "tenantId": "d3c0e3f9-060e-43d8-9d64-57fbb51d2003",
                        "name": null,
                        "aadObjectId": null,
                        "conversationType": "personal",
                        "properties": null,
                        "role": null,
                        "isGroup": null
                    },
                    "activityId": "f:c20375cb-8a88-6d68-8339-090d46d54fa0",
                    "serviceUrl": "https://smba.trafficmanager.net/emea/",
                    "bot": {
                        "name": "SuperBotFinal",
                        "id": "28:e250ed7c-49a9-46ab-9210-edf26cf4a221",
                        "role": null,
                        "aadObjectId": null
                    },
                    "locale": null,
                    "id": "a:1aStwF-......gUhlEo"
                }
            }
        
        """

        # # send request to PA
        # async with aiohttp.ClientSession() as session:
        #     # TODO(s1z): string bot's @mention if needed.
        #     message = turn_context.activity.text.strip().lower()
        #     data = dict(authorizartion=dict(token=reference),
        #                 reference=reference,
        #                 message=message)
        #     async with session.post(AppConfig.PA_URL, json=data) as resp:
        #         Log.e(TAG, f"on_message_activity::response.status:"
        #                    f"{resp.status}")
        #         rest_text = await resp.text()
        #         Log.e(TAG, f"on_message_activity::response.text: {rest_text}")
        #         return

        i18n = get_i18n(turn_context)

        if turn_context.activity.conversation.tenant_id != AppConfig.TENANT_ID:
            await turn_context.send_activity(i18n.t("tenant_forbidden"))
            return

        message = turn_context.activity.text.strip().lower()

        cmd_help = i18n.t("cmd_help")
        cmd_portal = i18n.t("cmd_portal")

        if message == cmd_help.lower():
            tenant_id = turn_context.activity.conversation.tenant_id
            conversation_id = turn_context.activity.conversation.id
            response = await turn_context.send_activity(
                i18n.t("response_help",
                       cmd_portal=cmd_portal,
                       cmd_help=cmd_help,
                       tenant_id=tenant_id,
                       conversation_id=conversation_id)
            )
            Log.d(TAG, "on_message_activity::help_resp: {}".format(response))
            return

        if message == cmd_portal.lower():
            card = CardHelper.load_assets_card("default_card")
            attachments = [CardFactory.adaptive_card(card)]
            message = Activity(type=ActivityTypes.message,
                               attachments=attachments)
            await turn_context.send_activity(message)
            return

        # TODO(s1z): Remove me when it's prod
        if message.find("flow") == 0:
            # Strip data again cause 'message' data is lower case
            params = turn_context.activity.text.strip().split(' ')
            if len(params) != 3:
                response = await turn_context.send_activity(
                    "Incorrect syntax. Please the syntax below:<br/>"
                    "  flow 'cmd' 'url'<br/><br/>"
                    "Where:<br/>"
                    "'cmd' - command you want to assing,<br/>"
                    "'url' - link of the flow you want it to be handled with."
                )
                Log.d(TAG,
                      "on_message_activity::help_resp: {}".format(response))
                return
            _, cmd, url = params
            # noinspection PyBroadException
            try:
                _ = await self.cosmos_client.create_flow(cmd, url)
                await turn_context.send_activity("Flow cmd saved")
                return
            except Exception:
                Log.e(TAG, f"on_message_activity::create_flow:error",
                      sys.exc_info())
                await turn_context.send_activity("Error saving flow cmd")
                return

        # try get flow link
        async def request():
            """ request """
            try:
                flow = await self.cosmos_client.get_flow(message)
                Log.e(TAG, f"on_message_activity::flow.url:{flow.url}")
                async with aiohttp.ClientSession() as session:
                    # TODO(s1z): string bot's @mention if needed.
                    data = dict(reference=reference, message=message)
                    async with session.post(flow.url, json=data) as resp:
                        Log.e(TAG, f"on_message_activity::response.status:"
                                   f"{resp.status}")
                        rest_text = await resp.text()
                        Log.e(TAG, f"on_message_activity::"
                                   f"response.text: {rest_text}")
                        return True
            except Exception:
                Log.e(TAG, f"on_message_activity::get_flow:error", sys.exc_info())
            return False
        response = await request()
        if response:
            return
        await turn_context.send_activity(i18n.t("response_unknown_cmd",
                                                cmd_help=cmd_help))

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
            Log.e(TAG, f"item '{notification_id}' not found")
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
        mx_object_key = "mx"

        # "mx": {
        #     "type": "task/notification",
        #     "notificationId": notification_id
        # }

        mx = MedX.get_schema(unknown=EXCLUDE).load(
            task_module_request.data.get(mx_object_key, dict())
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
