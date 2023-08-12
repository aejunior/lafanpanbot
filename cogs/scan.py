from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import discord
from helpers import db_manager as db, checks

from types import FunctionType as function
from typing import List

import requests
from urllib.parse import urlparse

from jikanpy import Jikan

from random import choice

jikan = Jikan(session=requests.Session())

def is_number(s):
    if s is None:
        return True
    if s.isdigit():
        return True
    try:
        float(s)
        return True
    except ValueError:
        return False

def format_text(id: str, type: str = "channel"):
    if type == "channel":
        text = f"<#{id}>" if id else "Nenhum"
    elif type == "role":
        if id == "@everyone":
            return id
        else: text = f"<@&{id}>" if id else "Nenhum"
    elif type == "user":
        text = f"<@{id}>" if id else "Nenhum"
        
    return text

def is_url(string):
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_mal_id(title):
  try:
    return bool(int(title))
  except:
    return False


async def role_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    roles = interaction.guild.roles
    return [
        app_commands.Choice(name=role.name, value=str(role.id)) for role in roles if current.lower() in role.name.lower()
    ]


async def manga_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    options = interaction.data["options"]
    option = next(item for item in options if item["name"] == "title" and item["focused"])
    
    r_jikan = jikan.search("manga", option["value"], parameters={"limit": 10})
    mangas = r_jikan.get("data")
    
    return [
        app_commands.Choice(name=manga.get("title"), value=str(manga.get("mal_id"))) for manga in mangas if current.lower() in manga.get("title").lower()
    ]


class Scan(commands.Cog, name="scan"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="settings",
        description="Configurações do servidor para scan",
    )
    @checks.is_owner()
    async def settings(self, context: Context):
        result = await db.get_setting(context.guild.id)
        if result is None:
            await db.add_setting(context.guild.id)
            result = await db.get_setting(context.guild.id)

        news_id= result[1]
        news_role_id = result[3]
        projects_id = result[2]

        news_text, projects_text, news_role_text = format_text(news_id), format_text(projects_id), format_text(news_role_id, "role")
        
        buttons = SettingsButtons()
        embed = discord.Embed(title=f"Configurações", color=0x9C84EF)
        embed.add_field(name="Notificações", value=f"Canal: {news_text}\nCargo: {news_role_text}")
        embed.add_field(name="Projetos", value=f"Canal: {projects_text}")
        message = await context.send(view=buttons, embed=embed, delete_after=15.0)

        await buttons.wait()
        if buttons.value == "exit":
            await message.delete()
        elif buttons.value == "pings":
            await message.delete()

            buttons = SettingsOptionsPings()
            embed = discord.Embed(title=f"Notificações", color=0x9C84EF)
            embed.add_field(name="Canal", value=news_text)
            embed.add_field(name="Cargo", value=news_role_text)
            message = await context.send(view=buttons, embed=embed, delete_after=15.0)

            await buttons.wait()
            if buttons.value == "exit":
                await message.delete()
            elif buttons.value == "role":
                await message.delete()

                buttons = SettingsOptionsSelected() if news_role_id else SettingsOptionsSelectedEmpty()
                embed = discord.Embed(title=f"Cargo para notificações", color=0x9C84EF)
                embed.add_field(name="Cargo", value=news_role_text)
                message =  await context.send(embed=embed, view=buttons, delete_after=15.0)

                await buttons.wait()
                if buttons.value == "exit":
                    await message.delete()
                elif buttons.value == "new":
                    await message.delete()

                    button = SettingsOptionsSelectedRole()
                    embed = discord.Embed(title=f"Cargo para notificações", color=0x9C84EF)
                    embed.add_field(name="Cargo", value=news_role_text)
                    message = await context.send(embed=embed, view=button, delete_after=15.0)

                    await button.wait()
                    if button.value == "choose":
                        await message.delete()

                        select = ChooseRoleView(pings_role_callback)
                        await context.send(view=select, delete_after=15.0)
                    elif button.value == "all":
                        await message.delete()

                        await db.set_setting(context.guild.id, news_role_id="@everyone")
                        await context.send("Todos serão notificados.", ephemeral=True)
                    if button.value == "exit":
                        await message.delete()
                elif buttons.value == "clear":
                    await message.delete()

                    await db.set_setting(context.guild.id, news_role_id=0)
                    await context.send("Cargo limpo.", ephemeral=True)
            elif buttons.value == "channel":
                await message.delete()
                
                buttons = SettingsOptionsSelected() if news_id else SettingsOptionsSelectedEmpty()
                embed = discord.Embed(title=f"Canal para notificações", color=0x9C84EF)
                embed.add_field(name="Canal", value=news_text)
                message = await context.send(embed=embed, view=buttons, delete_after=15.0)

                await buttons.wait()
                if buttons.value == "exit":
                    await message.delete()
                elif buttons.value == "new":
                    await message.delete()

                    select = ChooseChannelView(pings_callback)
                    await context.send(view=select, delete_after=15.0)
                elif buttons.value == "clear":
                    await message.delete()
                    
                    await db.set_setting(context.guild.id, news_id=0)
                    await context.send("Limpo.", ephemeral=True)
        elif buttons.value == "projects":
            await message.delete()

            buttons = SettingsOptionsSelected() if projects_id else SettingsOptionsSelectedEmpty()
            embed = discord.Embed(title=f"Projetos", color=0x9C84EF)
            embed.add_field(name="Canal", value=projects_text)
            message = await context.send(view=buttons, embed=embed, delete_after=15.0)

            await buttons.wait()
            if buttons.value == "clear":
                await message.delete()

                await db.set_setting(context.guild.id, projects_id=0)
                await context.send("Canal de notificações limpo.", ephemeral=True)
            elif buttons.value == "new":
                await message.delete()

                select = ChooseChannelView(projects_callback)
                await context.send(view=select, delete_after=15.0)
            elif buttons.value == "exit":
                await message.delete()

    @commands.hybrid_command(
        name="addproject",
        description="Adicione novos projetos",
    )
    @app_commands.autocomplete(title=manga_autocomplete)
    @app_commands.describe(
        title="Título ou ID MyAnimeList",
        description="Sinopse",
        mangalivre="URL MangaLivre",
        mangadex="URL MangaDex",
    )
    @checks.is_owner()
    async def new_project(self, context: Context, title: str, description: str, mangalivre:str = None, mangadex: str = None): #, genre: str, author: str ):
        result = await db.get_setting(context.guild.id)
        if result is None or result[2] is None:
            await context.interaction.response.send_message("Canal para projetos não definido!", ephemeral=True)
            return
        projects_id = result[2]
        channel = self.bot.get_channel(projects_id)
        if channel is None:
            await context.interaction.response.send_message("Canal para projetos não encontrado!", ephemeral=True)
            return
        
        if is_mal_id(title):
            r_jikan = jikan.manga(int(title))
            manga = r_jikan.get("data")
        else:
            r_jikan = jikan.search("manga", title, parameters={"limit": 1})
            manga = r_jikan.get("data")[0]

        embed = discord.Embed(
            title=manga.get("title"),
            url=manga.get("url"),
        )

        embed.add_field(name="Sinopse", value=description, inline=False)
        embed.add_field(name="Gênero(s)", value=", ".join([g.get("name") for g in manga.get("genres")]), inline=False)
        embed.add_field(name="Autor(es)", value=", ".join(["[{}]({})".format(a.get("name"), a.get("url")) for a in manga.get("authors")]))
        embed.set_image(url=manga.get("images").get("webp").get("large_image_url"))
        
        btns_ = ProjectButtons(mangalivre, mangadex)
        await channel.send(embed=embed, view=btns_)
        await context.reply("Projeto adicionado!", ephemeral=True)

    @commands.hybrid_command(
    name="addchapter",
    description="Novo capítulo",
    )
    @app_commands.autocomplete(title=manga_autocomplete, role=role_autocomplete)
    @app_commands.describe(
        title="Título",
        chapter="Número do capítulo",
        volume="Número do volume",
        mangalivre="URL MangaLivre",
        mangadex="URL MangaDex",
    )
    @checks.is_owner()
    async def new_chapter(self, context: Context, title: str, chapter: str, volume:str=None, role: str= None, mangalivre:str=None, mangadex: str=None):
        pings = [
            "Capítulo {number} de {title} lançado!\n{role}",
            "Capítulo {number} de {title} lançado! Vá ler...\n{role}",
            "Novo capítulo de {title}: {number}! Leitura imperdível!\n{role}",
            "{title} - Capítulo {number} acaba de ser lançado. Corra para conferir!\n{role}",
            "Prepare-se para emoções! Capítulo {number} de {title} já disponível!\n{role}",
            "Não perca tempo! {title} - Capítulo {number} acabou de ser publicado!\n{role}",
            "O aguardado capítulo {number} de {title} foi liberado. Aproveite a leitura!\n{role}",
            "Alerta de leitura! Capítulo {number} de {title} já está online!\n{role}",
            "{title} - Capítulo {number} está disponível. Não deixe de ler!\n{role}",
            "Lançamento fresquinho! {title} - Capítulo {number} acabou de ser lançado!\n{role}",
        ]

        if not is_number(chapter):
            await context.interaction.response.send_message("Número do capítulo inválido", ephemeral=True)
            return
        if not is_number(volume):
            await context.interaction.response.send_message("Número do volume inválido", ephemeral=True)
            return
        
        result = await db.get_setting(context.guild.id)
        guild_id, news_id, projects_id, news_role_id = result

        if result is None or news_id is None:
            await context.interaction.response.send_message("Canal para notificações não definido", ephemeral=True)
            return
        channel = self.bot.get_channel(news_id)
        if channel is None:
            await context.interaction.response.send_message("Canal para notificações não encontrado", ephemeral=True)
            return
        
        # if news_role_id is None:
        #     role = ""
        # else: 
        #     role = format_text(news_role_id, "role")
    
        r_jikan = jikan.manga(int(title))
        manga = r_jikan.get("data")
        embed = discord.Embed(
            title=manga.get("title"),
            url=manga.get("url"),
        )
        embed.set_image(url=manga.get("images").get("webp").get("large_image_url"))
        embed.add_field(name="Capítulo", value=chapter)
        if volume:
            embed.add_field(name="Volume", value=volume)
        if role:
            role = f"<@&{role}>"
        btns_ = ProjectButtons(mangalivre, mangadex)

        await channel.send(choice(pings).format(title=manga.get("title"), number=chapter, role=role), embed=embed, view=btns_)
        await context.reply("Capítulo adicionado!", ephemeral=True)
    
async def projects_callback(ctx, interaction: discord.Interaction):
    selected = interaction.data
    if selected:
        channel_id = selected["values"][0]
        await db.set_setting(interaction.guild_id, projects_id=channel_id)
        await interaction.message.delete()
        await interaction.response.send_message(f"Canal de projetos em: {format_text(channel_id)}", ephemeral=True)

async def pings_callback(ctx, interaction: discord.Interaction):
    selected = interaction.data
    if selected:
        channel_id = selected["values"][0]
        await db.set_setting(interaction.guild_id, news_id=channel_id)
        await interaction.message.delete()
        await interaction.response.send_message(f"Canal de notificações em: {format_text(channel_id)}", ephemeral=True)

async def pings_role_callback(ctx, interaction: discord.Interaction):
    selected = interaction.data
    if selected:
        role_id = selected["values"][0]
        await db.set_setting(interaction.guild_id, news_role_id=role_id)
        await interaction.message.delete()
        r = "role"
        await interaction.response.send_message(f"Leitores serão notificados em: {format_text(role_id, r)}.", ephemeral=True)

async def generic(ctx, interaction: discord.Interaction):
    print(ctx)
    print(interaction.data)

class ProjectButtons(discord.ui.View):
    def __init__(self, mangalivre: str, mangadex: str):
        super().__init__()
        self.value = None
        if is_url(mangalivre):
            ml = discord.ui.Button(label='MangáLivre', style=discord.ButtonStyle.url, url=mangalivre)
            self.add_item(ml)
        if is_url(mangadex):
            md = discord.ui.Button(label='MangaDex', style=discord.ButtonStyle.url, url=mangadex)
            self.add_item(md)
# Used
class SettingsOptionsPings(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Canal", style=discord.ButtonStyle.primary)
    async def channel(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "channel"
        self.stop()

    @discord.ui.button(label="Cargo", style=discord.ButtonStyle.primary)
    async def role(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "role"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def exit(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

# Used
class SettingsButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Notificações", style=discord.ButtonStyle.primary)
    async def news(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "pings"
        self.stop()

    @discord.ui.button(label="Projetos", style=discord.ButtonStyle.primary)
    async def projects(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "projects"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

# Clear, new and exit
class SettingsOptionsSelected(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Limpar", style=discord.ButtonStyle.primary)
    async def clear(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "clear"
        self.stop()

    @discord.ui.button(label="Selecionar", style=discord.ButtonStyle.primary)
    async def select(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "new"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

class SettingsOptionsSelectedEmpty(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Selecionar", style=discord.ButtonStyle.primary)
    async def select(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "new"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

class SettingsOptionsSelectedRole(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Escolher", style=discord.ButtonStyle.primary)
    async def choose(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "choose"
        self.stop()

    @discord.ui.button(label="Todos", style=discord.ButtonStyle.primary)
    async def all(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "all"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

# Select role
class ChooseRole(discord.ui.RoleSelect):
    def __init__(self, callback: function):
        super().__init__()
        self.custom_id = "role_select"
        self.min_values = 1
        self.max_values = 1
        self.cb = callback

    async def callback(self, interaction: discord.Interaction):
        await self.cb(self, interaction)

class ChooseRoleView(discord.ui.View):
    def __init__(self, cb: function = generic):
        super().__init__()
        self.add_item(ChooseRole(cb))

# Select channel
class ChooseChannel(discord.ui.ChannelSelect):
    def __init__(self, callback: function):
        super().__init__()
        self.channel_types = [discord.ChannelType.text]
        self.custom_id = "channel_select"
        self.min_values = 1
        self.max_values = 1
        self.cb = callback

    async def callback(self, interaction: discord.Interaction):
        await self.cb(self, interaction)

class ChooseChannelView(discord.ui.View):
    def __init__(self, cb: function = generic):
        super().__init__()
        self.add_item(ChooseChannel(cb))

async def setup(bot):
    await bot.add_cog(Scan(bot))
