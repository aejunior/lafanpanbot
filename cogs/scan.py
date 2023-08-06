from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import discord
from helpers import checks, db_manager
from helpers import db_manager as db 

from types import FunctionType as function
from typing import List

import requests
from urllib.parse import urlparse

from jikanpy import Jikan

from random import choice


jikan = Jikan(session=requests.Session())

def is_number(s):
    if s.isdigit():
        return True
    try:
        float(s)
        return True
    except ValueError:
        return False

def format_text(id: str):
    text = f"<#{id}>" if id else "Nenhum"
    return text

def is_url(string):
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

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
        projects_id = result[2]
        
        embed = discord.Embed(description=f"Configurações", color=0x9C84EF)
        news_text, projects_text = format_text(news_id), format_text(projects_id)
        embed.add_field(name="Notificações", value=f"Canal: {news_text}")
        embed.add_field(name="Projetos", value=f"Canal: {projects_text}")

        buttons = SettingsButtons()
        message = await context.send(view=buttons, embed=embed)
        await buttons.wait()

        if buttons.value == "exit":
            await message.delete()
            return
        elif buttons.value == "pings":
            await message.delete()
            buttons_ = SettingsButtonsSelected() if news_id else SettingsButtonsSelectedEmpty()

            embed = discord.Embed(description=f"Notificações", color=0x9C84EF)
            embed.add_field(name="Canal", value=news_text)

            message_ = await context.send("Notificações", view=buttons_, embed=embed)
            await buttons_.wait()

            menu = ChooseSettingsView(pings_callback)

            if buttons_.value == "clear":
                await db.set_setting(context.guild.id, news_id=0)
                ping_message_ = await context.send("Limpo", ephemeral=True)
            elif buttons_.value == "select":
                embed = discord.Embed(description=f"Escolha o canal para notificações", color=0x9C84EF)
                ping_message_ = await context.send(embed=embed, view=menu)
            elif buttons_.value == "exit":
                await message_.delete()
                return
            await message_.delete()

        elif buttons.value == "projects":
            await message.delete()
            buttons_ = SettingsButtonsSelected() if projects_id else SettingsButtonsSelectedEmpty()

            embed = discord.Embed(description=f"Projetos", color=0x9C84EF)
            embed.add_field(name="Canal", value=projects_text)
            
            message_ = await context.send("Projetos", view=buttons_, embed=embed)
            await buttons_.wait()
            
            menu = ChooseSettingsView(projects_callback)

            if buttons_.value == "clear":
                await db.set_setting(context.guild.id, projects_id=0)
                ping_message_ = await context.send("Limpo", ephemeral=True)
            elif buttons_.value == "select":
                embed = discord.Embed(description=f"Escolha o canal para projetos", color=0x9C84EF)
                ping_message_ = await context.send(embed=embed, view=menu)
            elif buttons_.value == "exit":
                await message_.delete()
                return
            await message_.delete()


    @commands.hybrid_command(
        name="addproject",
        description="Adicione novos projetos",
    )
    @app_commands.autocomplete(title=manga_autocomplete)
    @app_commands.describe(
        title="Título",
        description="Sinopse",
        mangalivre="URL MangaLivre",
        mangadex="URL MangaDex",
    )
    @checks.is_owner()
    async def new_project(self, context: Context, title: str, mangalivre:str, mangadex: str, description: str): #, genre: str, author: str ):
        result = await db.get_setting(context.guild.id)
        if result is None or result[2] is None:
            await context.interaction.response.send_message("Canal para projetos não definido", ephemeral=True)
            return
        projects_id = result[2]
        channel = self.bot.get_channel(projects_id)
        if channel is None:
            await context.interaction.response.send_message("Canal para projetos não encontrado", ephemeral=True)
            return
        
        r_jikan = jikan.manga(int(title))
        manga = r_jikan.get("data")

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
    
    
    @app_commands.autocomplete(title=manga_autocomplete)
    @app_commands.describe(
        title="Título",
        chapter="Número do capítulo",
        volume="Número do volume",
        mangalivre="URL MangaLivre",
        mangadex="URL MangaDex",
    )
    @checks.is_owner()
    async def new_chapter(self, context: Context, title: str, chapter: str, volume:str, mangalivre:str, mangadex: str):
        pings = [
            "Capítulo {number} de {title} lançado!",
            "Capítulo {number} de {title} lançado! Vá ler...",
            "Novo capítulo de {title}: {number}! Leitura imperdível!",
            "{title} - Capítulo {number} acaba de ser lançado. Corra para conferir!",
            "Prepare-se para emoções! Capítulo {number} de {title} já disponível!",
            "Não perca tempo! {title} - Capítulo {number} acabou de ser publicado!",
            "O aguardado capítulo {number} de {title} foi liberado. Aproveite a leitura!",
            "Alerta de leitura! Capítulo {number} de {title} já está online!",
            "{title} - Capítulo {number} está disponível. Não deixe de ler!",
            "Lançamento fresquinho! {title} - Capítulo {number} acabou de ser lançado!",
        ]

        result = await db.get_setting(context.guild.id)
        if result is None or result[1] is None:
            await context.interaction.response.send_message("Canal para notificações não definido", ephemeral=True)
            return
        news_id = result[1]
        channel = self.bot.get_channel(news_id)
        if channel is None:
            await context.interaction.response.send_message("Canal para notificações não encontrado", ephemeral=True)
            return
        
        r_jikan = jikan.manga(int(title))
        manga = r_jikan.get("data")
        print(manga)
        embed = discord.Embed(
            title=manga.get("title"),
            url=manga.get("url"),
        )
        embed.set_image(url=manga.get("images").get("webp").get("large_image_url"))
        embed.add_field(name="Capítulo", value=chapter)
        embed.add_field(name="Volume", value=chapter)
        
        btns_ = ProjectButtons(mangalivre, mangadex)
        await channel.send(choice(pings).format(title=manga.get("title"), number=chapter), embed=embed, view=btns_)
        await context.reply("Capítulo adicionado!", ephemeral=True)
    
async def projects_callback(ctx, interaction: discord.Interaction):
    selected = interaction.data
    if selected:
        channel_id = selected["values"][0]
        await db.set_setting(interaction.guild_id, projects_id=channel_id)
        await interaction.message.delete()
        await interaction.response.send_message(f"Canal de projetos definido para <#{channel_id}>", ephemeral=True)

async def pings_callback(ctx, interaction: discord.Interaction):
    selected = interaction.data
    if selected:
        channel_id = selected["values"][0]
        await db.set_setting(interaction.guild_id, news_id=channel_id)
        await interaction.message.delete()
        await interaction.response.send_message(f"Canal de projetos definido para <#{channel_id}>", ephemeral=True)

async def generic(ctx, interaction: discord.Interaction):
    print(ctx)
    print(interaction.data)

class SettingsPingsOption(discord.ui.ChannelSelect):
    def __init__(self, callback: function):
        super().__init__()
        self.custom_id = "channel_select"
        self.channel_types = [discord.ChannelType.text]
        self.min_values = 1
        self.max_values = 1
        self.cb = callback

    async def callback(self, interaction: discord.Interaction):
        await self.cb(self, interaction)

class ChooseSettingsView(discord.ui.View):
    def __init__(self, cb: function = generic):
        super().__init__()
        self.add_item(SettingsPingsOption(cb))

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

class SettingsButtonsSelected(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Limpar", style=discord.ButtonStyle.primary)
    async def clear(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "clear"
        self.stop()

    @discord.ui.button(label="Novo", style=discord.ButtonStyle.primary)
    async def select(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "select"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()

class SettingsButtonsSelectedEmpty(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Novo", style=discord.ButtonStyle.primary)
    async def select(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "select"
        self.stop()

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "exit"
        self.stop()


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


async def setup(bot):
    await bot.add_cog(Scan(bot))
