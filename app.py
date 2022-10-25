""" Bot App """
import json
import sys
import traceback
from datetime import datetime
from http import HTTPStatus

import marshmallow_dataclass as m_d
from aiohttp import web
from aiohttp.web import Request, Response, json_response
from aiohttp.web_fileresponse import FileResponse
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.schema import Activity, ActivityTypes
from marshmallow import EXCLUDE, ValidationError

from bots import TeamsMessagingExtensionsActionPreviewBot
from bots.exceptions import ConversationNotFound, DataParsingError
from config import AppConfig, COSMOS_CLIENT, KEY_VAULT_CLIENT, TeamsAppConfig, \
    TOKEN_HELPER
from entities.json.admin_user import AdminUser
from entities.json.notification import Notification
from utils.cosmos_client import ItemNotFound
from utils.json_func import json_loads, json_dumps
from utils.log import Log
from utils.teams_app_generator import TeamsAppGenerator

app_config = AppConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
app_settings = BotFrameworkAdapterSettings(app_config.APP_ID,
                                           app_config.APP_PASSWORD)

ADAPTER = BotFrameworkAdapter(app_settings)
TAG = __name__


# noinspection PyShadowingNames
async def on_error(context: TurnContext, error: Exception):
    """ Executed on any error """
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment,
    #       you should consider logging this to Azure application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity(
        "The bot encountered an error or bug.\r\n"
        "To continue to run this bot, please fix the bot source code."
    )

    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity,
        # which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error
BOT = TeamsMessagingExtensionsActionPreviewBot(app_settings, ADAPTER)


@TOKEN_HELPER.is_auth
async def v1_get_initiations(request: Request) -> Response:
    """ Get Initiations by Notification ID """
    # noinspection PyBroadException
    try:
        notification_id = request.match_info['notification_id']
        inits = await COSMOS_CLIENT.get_initiation_items(notification_id)
        data = dict(data=[dict(initiator=init.initiator,
                               timestamp=init.timestamp,
                               id=init.id) for init in inits])
        return Response(body=json.dumps(data), status=HTTPStatus.OK)
    except ItemNotFound as e:
        Log.e(TAG, "v1_get_initiations::item not found", e)
        return Response(status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        Log.e(TAG, "v1_get_initiations::exception", sys.exc_info())
    return Response(status=HTTPStatus.BAD_REQUEST)


@TOKEN_HELPER.is_auth
async def v1_get_notification(request: Request) -> Response:
    """ Get Notification by ID """
    # noinspection PyBroadException
    try:
        notification_id = request.match_info['notification_id']
        notification = await COSMOS_CLIENT.get_notification(notification_id)
        acks = await COSMOS_CLIENT.get_acknowledge_items(notification_id)
        data = dict(data=dict(
            timestamp=notification.timestamp,
            status="DELIVERED",
            acknowledged=[dict(username=ack.username,
                               timestamp=ack.timestamp) for ack in acks],
        ))
        return Response(body=json.dumps(data), status=HTTPStatus.OK)
    except ItemNotFound as e:
        Log.e(TAG, "v1_get_notification::item not found", e)
        return Response(status=HTTPStatus.NOT_FOUND)
    except Exception:
        Log.e(TAG, exc_info=sys.exc_info())
    return Response(status=HTTPStatus.BAD_REQUEST)


@TOKEN_HELPER.is_auth
async def v1_notification(request: Request) -> Response:
    """ Notify channel with the link """
    # todo(s1z): add auth
    # noinspection PyBroadException
    try:
        request_body = await request.text()
        schema = Notification.get_schema(unknown=EXCLUDE)
        notification = schema.load(json_loads(request_body, {})).to_db()
        message_id = await BOT.send_notification(notification)
        response_body = json.dumps({"data": {"messageId": message_id}})
        return Response(body=response_body, status=HTTPStatus.OK)
    except ConversationNotFound:
        return Response(status=HTTPStatus.NOT_FOUND,
                        reason="Conversation not found")
    except DataParsingError:
        return Response(status=HTTPStatus.BAD_REQUEST,
                        reason="Bad data structure")
    except Exception as e:
        print("error:", e)
        return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)


async def v1_messages(request: Request) -> Response:
    """ messages endpoint """
    if "application/json" in request.headers["Content-Type"]:
        body = await request.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = (request.headers["Authorization"]
                   if "Authorization" in request.headers else "")

    invoke_response = await ADAPTER.process_activity(
        activity, auth_header, BOT.on_turn
    )
    if invoke_response:
        return json_response(data=invoke_response.body,
                             status=invoke_response.status)
    return Response(status=HTTPStatus.OK)


async def v1_health_check(_request: Request) -> Response:
    """ Health check """
    try:
        _container = await COSMOS_CLIENT.get_conversations_container()
        _data = (await KEY_VAULT_CLIENT.get_secret("adminLogin")).value
        # key = await KEY_VAULT_CLIENT.create_key("pumpalot")
        # encrypted_data = await KEY_VAULT_CLIENT.encrypt(key, b"hello")
        # decrypted_data = await KEY_VAULT_CLIENT.decrypt(key, encrypted_data)
        Log.i(TAG, "v1_health_check::ok")
        return Response(status=HTTPStatus.OK)
    except Exception as e:
        Log.e(TAG, f"v1_health_check::error:{e}", sys.exc_info())
        raise


async def get_app_zip(_request: Request) -> FileResponse:
    """ Get zip file """
    await TeamsAppGenerator.generate_zip()
    return FileResponse(path=TeamsAppConfig.zip_file)


@web.middleware
async def error_middleware(request, handler):
    """ Error handler """
    try:
        response = await handler(request)
        if response.status != 404:
            return response
        message = response.reason
    except web.HTTPException as ex:
        if ex.status != 404:
            raise
        message = ex.reason
    return Response(status=HTTPStatus.NOT_FOUND,
                    body=json.dumps({"error": message}))


async def v1_auth(request: Request) -> Response:
    """ Admin Auth """
    if "application/json" in request.headers["Content-Type"]:
        body = await request.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    try:
        admin_user = AdminUser.Schema().load(body)
        if admin_user.login and admin_user.password:
            result = await TOKEN_HELPER.do_auth(admin_user)
            if result is not None:
                return Response(status=HTTPStatus.OK, body=json_dumps(result))
    except ValidationError:
        pass
    return Response(status=HTTPStatus.FORBIDDEN)


APP = web.Application(middlewares=[error_middleware])
APP.router.add_post("/api/v1/messages", v1_messages)
APP.router.add_post("/api/v1/notification", v1_notification)
APP.router.add_get("/api/v1/notification/{notification_id}",
                   v1_get_notification)
APP.router.add_get("/api/v1/initiations/{notification_id}", v1_get_initiations)
APP.router.add_get("/api/v1/health-check", v1_health_check)
APP.router.add_get("/{}".format(TeamsAppConfig.zip_name), get_app_zip)
APP.router.add_post("/api/v1/auth", v1_auth)


BOT.add_web_app(APP)
BOT.add_cosmos_client(COSMOS_CLIENT)


if __name__ == "__main__":
    try:
        web.run_app(APP, host="0.0.0.0", port=app_config.PORT)
    except Exception as error:
        raise error
