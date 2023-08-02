""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""
from discord import app_commands

from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks


# Here we name the cog and create a new class for the cog.
class Scan(commands.Cog, name="scan"):
    def __init__(self, bot):
        self.bot = bot

    # Here you can just add your own commands, you'll always need to provide "self" as first parameter.

    @commands.hybrid_command(
        name="posted",
        description="This is a testing command that does nothing.",
    )
    # This will only allow non-blacklisted members to execute the command
    @checks.not_blacklisted()
    @app_commands.describe(
        # Adding list of options to the command
        title="Nome do mangá",
        # Regex with valid number of chapter
        chapter="Número do capítulo",
        url="URL do mangá",
        cover="Capa do mangá",
        )
    # This will only allow owners of the bot to execute the command -> config.json
    @checks.is_owner()
    async def posted(self, context: Context, title: str, chapter: str, url: str, cover: str):
        """
        This is a testing command that does nothing.

        :param context: The application command context.
        """
        # Do your stuff here

        # Don't forget to remove "pass", I added this just because there's no content in the method.
        pass


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    await bot.add_cog(Scan(bot))
