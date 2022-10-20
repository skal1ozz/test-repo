""" Teams App Generator """
import asyncio
import json
import os
from zipfile import ZipFile, ZIP_DEFLATED

from config import AppConfig, TeamsAppConfig

manifest = {
    "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.14/MicrosoftTeams.schema.json",
    "version": "1.0.0",
    "manifestVersion": "1.0.0",
    # "id": "THIS IS AN APP SERVICE ID",
    # "packageName": "net.azurewebsites.bot-name",
    # "name": {
    #     "short": "Cakebot-3",
    #     "full": "Cakebot-3"
    # },
    "developer": {
        "name": "Medxnote",
        "mpnId": "",
        "websiteUrl": "https://medxnote.com",
        "privacyUrl": "https://medxnote.com/privacy-policy/",
        "termsOfUseUrl": "https://medxnote.com/terms-conditions/"
    },
    "description": {
        "short": "Cakebot-3", "full": "Cakebot-3 Bot"
    },
    # "icons": {
    #     "outline": "outline.png",
    #     "color": "color.png"
    # },
    "accentColor": "#ffffff",
    "staticTabs": [
        {"entityId": "conversations", "scopes": ["personal"]},
        {"entityId": "about", "scopes": ["personal"]}
    ],
    # "bots": [
    #     {
    #         "botId": "THIS IS A BOT SERVICE ID",
    #         "scopes": ["personal", "team", "groupchat"],
    #         "isNotificationOnly": False,
    #         "supportsCalling": False,
    #         "supportsVideo": False,
    #         "supportsFiles": False
    #     }
    # ],
    "validDomains": [],
    # "webApplicationInfo": {"id": "THIS IS AN APP SERVICE ID",
    #                        "resource": ""},
    "authorization": {"permissions": {"resourceSpecific": []}}
}


class TeamsAppGenerator:
    """ Teams App Generator implementation """

    @staticmethod
    def gen_manifest():
        """ Generate manifest """
        # ID
        manifest.update(dict(id=AppConfig.APP_ID))
        # Package name
        manifest.update(dict(
            packageName="net.azurewebsites.{}".format(AppConfig.WEB_APP_NAME)
        ))
        # Namings
        details = dict(short=AppConfig.BOT_NAME,
                       full=AppConfig.BOT_NAME)
        manifest.update(dict(name=details))
        manifest.update(dict(description=details))

        # Bot
        bot = dict(botId=AppConfig.CLIENT_ID,
                   scopes=["personal", "team", "groupchat"],
                   isNotificationOnly=False,
                   supportsCalling=False,
                   supportsVideo=False,
                   supportsFiles=False)
        manifest.update(dict(bots=[bot, ]))
        # WebAppInfo
        web_app_info = dict(id=AppConfig.APP_ID, resource="")
        manifest.update(dict(webApplicationInfo=web_app_info))
        #
        with open(TeamsAppConfig.manifest, "w") as f:
            f.write(json.dumps(manifest))
            f.flush()
        return TeamsAppConfig.manifest

    @staticmethod
    def generate_zip_bl():
        """ Generate zip blocking """
        TeamsAppGenerator.gen_manifest()
        with ZipFile(TeamsAppConfig.zip_file, "w", ZIP_DEFLATED) as zip_file:
            for file in [TeamsAppConfig.manifest,
                         TeamsAppConfig.image_32x32,
                         TeamsAppConfig.image_192x192]:
                file_name = os.path.basename(file)
                zip_file.write(file, arcname=file_name)

    @staticmethod
    async def generate_zip():
        """ Generate the app """
        io_loop = asyncio.get_event_loop()
        await io_loop.run_in_executor(None, TeamsAppGenerator.generate_zip_bl)
