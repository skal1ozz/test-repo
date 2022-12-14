""" Bot App """
import json
import sys
import time
import traceback
from datetime import datetime
from http import HTTPStatus
from typing import Dict, Union, List

import marshmallow_dataclass
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

from bots.messaging_extension_action_preview_bot import \
    TeamsMessagingExtensionsActionPreviewBot
from bots.exceptions import ConversationNotFound, DataParsingError
from config import AppConfig, COSMOS_CLIENT, TeamsAppConfig, TOKEN_HELPER, \
    CosmosDBConfig
from entities.json.admin_user import AdminUser
from entities.json.notification import Notification
from entities.json.pa_message import PAMessage
from utils.cosmos_client import ItemNotFound
from utils.functions import quote_b64encode_str_safe, quote_b64decode_str_safe
from utils.json_func import json_loads, json_dumps
from utils.log import Log, init_logging
from utils.teams_app_generator import TeamsAppGenerator

app_config = AppConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
app_settings = BotFrameworkAdapterSettings(app_config.APP_ID,
                                           app_config.APP_PASSWORD)

ADAPTER = BotFrameworkAdapter(app_settings)
BOT = TeamsMessagingExtensionsActionPreviewBot(app_settings, ADAPTER)
TAG = __name__


# noinspection PyShadowingNames
async def on_error(context: TurnContext, error: Exception):
    """ Executed on any error """
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment,
    #       you should consider logging this to Azure application insights.
    Log.e(TAG, f"\n [on_turn_error] unhandled error: {error}")
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


def make_response(code: int, message: str,
                  data: Union[Dict[any, any], List[Dict[any, any]]] = None)\
        -> Response:
    """ Make an API json response """
    body = dict(status=dict(code=code, message=message))
    if data is not None:
        body.update(dict(data=data))
    return Response(status=HTTPStatus.OK, body=json_dumps(body))


@TOKEN_HELPER.is_auth
async def v1_get_initiations(request: Request) -> Response:
    """ Get Initiations by Notification ID """
    # noinspection PyBroadException
    try:
        query_token = request.query.get("token")
        Log.d(TAG, "v1_get_initiations::query_token: {}".format(query_token))

        token = quote_b64decode_str_safe(query_token)
        notification_id = request.match_info.get('notification_id')
        Log.d(TAG, "v1_get_initiations::notification_id: "
                   "{}".format(notification_id))
        init_items, paging_token = await COSMOS_CLIENT.get_initiation_items(
            notification_id, token
        )
        data = dict(initiators=[dict(initiator=i.initiator,
                                     timestamp=i.timestamp,
                                     id=i.id) for i in init_items])
        Log.d(TAG, "v1_get_initiations::paging_token: {}".format(paging_token))
        if paging_token is not None:
            token_encoded = quote_b64encode_str_safe(paging_token)
            data.update(dict(paging=dict(token=token_encoded)))

        body = dict(status=dict(message="OK", code=200), data=data)
        return Response(body=json.dumps(body), status=HTTPStatus.OK)
    except ItemNotFound:
        Log.e(TAG, "v1_get_initiations::item not found", sys.exc_info())
        return Response(status=HTTPStatus.NOT_FOUND)
    except Exception:
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
            status="DELIVERED",  # TODO(s1z): insert a real status value pls!
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
async def v1_post_notification(request: Request) -> Response:
    """ Notify channel with the link """
    # noinspection PyBroadException
    try:
        request_body = await request.text()
        schema = Notification.get_schema(unknown=EXCLUDE)
        notification = schema.load(json_loads(request_body, {})).to_db()
        notification_id = await BOT.send_notification(notification)
        data = dict(notificationId=notification_id)
        body = dict(status=dict(message="OK", code=200), data=data)
        return Response(body=json.dumps(body), status=HTTPStatus.OK)
    except ConversationNotFound:
        return Response(status=HTTPStatus.NOT_FOUND,
                        reason="Conversation not found")
    except DataParsingError:
        return Response(status=HTTPStatus.BAD_REQUEST,
                        reason="Bad data structure")
    except Exception:
        Log.e(TAG, exc_info=sys.exc_info())
        return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)


async def v1_messages(request: Request) -> Response:
    """ messages endpoint """
    start = time.time()
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
    took = time.time() - start
    Log.d(TAG, f"v1_messages::nessage handling took: {took} seconds")
    return Response(status=HTTPStatus.OK)


async def v1_get_health_check(_request: Request) -> Response:
    """ Health check """
    try:
        # _container = await COSMOS_CLIENT.get_conversations_container()
        # _data = (await KEY_VAULT_CLIENT.get_secret("adminLogin")).value
        # key = await KEY_VAULT_CLIENT.create_key("pumpalot")
        # encrypted_data = await KEY_VAULT_CLIENT.encrypt(key, b"hello")
        # decrypted_data = await KEY_VAULT_CLIENT.decrypt(key, encrypted_data)
        Log.i(TAG, "v1_health_check::ok")
        return Response(status=HTTPStatus.OK, content_type="application/json")
    except Exception as e:
        Log.e(TAG, f"v1_health_check::error:{e}", sys.exc_info())
        raise


async def v1_get_app_zip(_request: Request) -> FileResponse:
    """ Get zip file """
    from config import APP_VERSION
    filename = f"app_{APP_VERSION}.zip"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    await TeamsAppGenerator.generate_zip()
    return FileResponse(path=TeamsAppConfig.zip_file, headers=headers)


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


async def v1_post_auth(request: Request) -> Response:
    """ Admin Auth """
    if "application/json" in request.headers["Content-Type"]:
        body = await request.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    try:
        admin_user = marshmallow_dataclass.class_schema(AdminUser)().load(body)
        if admin_user.login and admin_user.password:
            result = await TOKEN_HELPER.do_auth(admin_user)
            if result is not None:
                body = dict(status=dict(message="OK", code=200),
                            data=result)
                return Response(status=HTTPStatus.OK, body=json_dumps(body))
    except ValidationError:
        pass
    return Response(status=HTTPStatus.FORBIDDEN)


async def v1_pa_message(request: Request) -> Response:
    """ Send card to the bot """
    # noinspection PyBroadException
    try:
        body = json_loads(await request.text())
        pa_message = PAMessage.get_schema().load(body)
        response = await BOT.send_message(pa_message.conversation_id,
                                          pa_message.tenant_id,
                                          pa_message.text,
                                          pa_message.card,
                                          pa_message.cards)
        Log.d(TAG, f"v1_pa_message::notification: '{response}'")
        return make_response(200, "OK")
    except Exception:
        Log.e(TAG, "v1_pa_message::error sending message",
              exc_info=sys.exc_info())
        return make_response(500, "Server Error")
    return make_response(400, "Bad Request")


async def v1_pa_authorize(request: Request) -> Response:
    """ Authorize Power Automate flow token """
    # noinspection PyBroadException
    try:
        data = json_loads(await request.text())
        if data is not None:
            return make_response(200, "OK")
    except Exception:
        Log.e(TAG, "v1_pa_authorize::error sending message",
              exc_info=sys.exc_info())
        return make_response(500, "Server Error")
    # TODO(s1z): Change thit to 400 when auth is enabled!!!
    return make_response(200, "Bad Request")


async def init_db_containers():
    """ To speed up the process we have to create containers first """
    await COSMOS_CLIENT.create_db(CosmosDBConfig.Conversations.DATABASE)
    await COSMOS_CLIENT.create_container(
        CosmosDBConfig.Conversations.DATABASE,
        CosmosDBConfig.Conversations.CONTAINER,
        CosmosDBConfig.Conversations.PARTITION_KEY
    )
    await COSMOS_CLIENT.create_container(
        CosmosDBConfig.Notifications.DATABASE,
        CosmosDBConfig.Notifications.CONTAINER,
        CosmosDBConfig.Notifications.PARTITION_KEY
    )
    await COSMOS_CLIENT.create_container(
        CosmosDBConfig.Acknowledges.DATABASE,
        CosmosDBConfig.Acknowledges.CONTAINER,
        CosmosDBConfig.Acknowledges.PARTITION_KEY
    )
    await COSMOS_CLIENT.create_container(
        CosmosDBConfig.Initiations.DATABASE,
        CosmosDBConfig.Initiations.CONTAINER,
        CosmosDBConfig.Initiations.PARTITION_KEY
    )
    await COSMOS_CLIENT.create_container(
        CosmosDBConfig.Flows.DATABASE,
        CosmosDBConfig.Flows.CONTAINER,
        CosmosDBConfig.Flows.PARTITION_KEY
    )


async def app_factory(bot):
    """ Create the app """

    await init_db_containers()

    app = web.Application(middlewares=[error_middleware])
    app.router.add_post("/api/v1/messages", v1_messages)
    app.router.add_post("/api/v1/notification", v1_post_notification)
    app.router.add_get("/api/v1/notification/{notification_id}",
                       v1_get_notification)
    app.router.add_get("/api/v1/initiations/{notification_id}",
                       v1_get_initiations)
    app.router.add_get("/api/v1/health-check", v1_get_health_check)
    app.router.add_get("/{}".format(TeamsAppConfig.zip_name), v1_get_app_zip)
    app.router.add_post("/api/v1/auth", v1_post_auth)

    # PA endpoints
    app.router.add_post("/api/pa/v1/message", v1_pa_message)
    app.router.add_post("/api/pa/v1/authorize", v1_pa_authorize)
    bot.add_web_app(app)
    bot.add_cosmos_client(COSMOS_CLIENT)

    return app


if __name__ == "__main__":
    init_logging()
    try:
        web.run_app(app_factory(BOT), host="0.0.0.0", port=app_config.PORT)
    except Exception as error:
        raise error
