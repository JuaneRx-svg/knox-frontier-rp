# ============================================================
#   KNOX FRONTIER RP — Discord Bot
#   Requiere: pip install discord.py mcrcon
# ============================================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import mcrcon
import subprocess
import asyncio
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────
#   CONFIGURACIÓN — EDITA ESTOS VALORES
# ─────────────────────────────────────────
TOKEN            = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_NAME  = "Staff"          # Rol que puede usar comandos del servidor
PREFIX           = "!"

# Servidor PZ
PZ_EXE_PATH      = r"C:\ruta\al\servidor\StartServer64.bat"
RCON_HOST        = "127.0.0.1"
RCON_PORT        = 27015
RCON_PASSWORD    = "only2830"
SERVER_PUBLIC_IP = "92.38.150.78"
SERVER_PORT      = 60403

# Rutas de logs PZ (carpeta Zomboid\Logs)
LOGS_PATH        = r"C:\Users\TU_USUARIO\Zomboid\Logs"

# IDs de canales — reemplaza con los IDs reales de tu Discord
CHANNEL_LOGS     = 1511504723801411806
CHANNEL_WELCOME  = 1511505540872929300
CHANNEL_ANUNCIOS = 1511505569918222479
CHANNEL_GENERAL  = 1511505594064834701

# ─────────────────────────────────────────
#   SETUP DEL BOT
# ─────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
tree = bot.tree

spam_tracker = defaultdict(list)   # user_id -> [timestamps]
log_position = {}                  # archivo -> posición leída

# ─────────────────────────────────────────
#   HELPERS
# ─────────────────────────────────────────
def is_staff():
    async def predicate(ctx):
        role = discord.utils.get(ctx.guild.roles, name=STAFF_ROLE_NAME)
        return role in ctx.author.roles
    return commands.check(predicate)

def is_staff_interaction(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    return role in interaction.user.roles

async def rcon_command(cmd: str) -> str:
    try:
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            return mcr.command(cmd)
    except Exception as e:
        return f"❌ Error RCON: {e}"

def knox_embed(title, description, color=0xCC2222):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
    embed.set_footer(text="Knox Frontier RP")
    return embed

# ─────────────────────────────────────────
#   EVENTOS
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    watch_logs.start()
    print(f"✅ Knox Bot online como {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Knox Frontier RP | !info"))

@bot.event
async def on_member_join(member):
    if CHANNEL_WELCOME == 0:
        return
    channel = bot.get_channel(CHANNEL_WELCOME)
    embed = knox_embed(
        "🧟 Nuevo superviviente en Knox County",
        f"Bienvenido/a **{member.mention}** a **Knox Frontier RP**.\n\n"
        f"📜 Lee las reglas antes de unirte al servidor.\n"
        f"🎮 IP: `{SERVER_PUBLIC_IP}:{SERVER_PORT}`\n"
        f"Sobrevive. Construye tu historia. Crea tu legado.",
        color=0xCC2222
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)

    # Asignar rol automático de superviviente
    survivor_role = discord.utils.get(member.guild.roles, name="Superviviente")
    if survivor_role:
        await member.add_roles(survivor_role)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Anti-spam: máx 5 mensajes en 5 segundos
    now = datetime.utcnow()
    uid = message.author.id
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < timedelta(seconds=5)]
    spam_tracker[uid].append(now)

    if len(spam_tracker[uid]) >= 5:
        await message.delete()
        staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
        if not (staff_role and staff_role in message.author.roles):
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Anti-spam automático")
                await message.channel.send(
                    f"⚠️ {message.author.mention} detectado como spam. Timeout de 5 minutos.",
                    delete_after=10
                )
            except:
                pass
        return

    await bot.process_commands(message)

# ─────────────────────────────────────────
#   COMANDOS DE PREFIJO — SERVIDOR PZ
# ─────────────────────────────────────────
@bot.command(name="start")
@is_staff()
async def cmd_start(ctx):
    embed = knox_embed("🚀 Iniciando servidor", "El servidor de Knox Frontier RP está arrancando...", 0x00AA44)
    await ctx.send(embed=embed)
    subprocess.Popen(PZ_EXE_PATH, shell=True)

@bot.command(name="stop")
@is_staff()
async def cmd_stop(ctx):
    result = await rcon_command("quit")
    embed = knox_embed("🛑 Apagando servidor", f"Servidor detenido.\n```{result}```", 0xCC2222)
    await ctx.send(embed=embed)

@bot.command(name="restart")
@is_staff()
async def cmd_restart(ctx):
    embed = knox_embed("🔄 Reiniciando servidor", "Enviando aviso a jugadores...", 0xFFAA00)
    await ctx.send(embed=embed)
    await rcon_command('servermsg "El servidor se reiniciará en 1 minuto. Guarda tu progreso."')
    await asyncio.sleep(60)
    await rcon_command("quit")
    await asyncio.sleep(5)
    subprocess.Popen(PZ_EXE_PATH, shell=True)
    await ctx.send(embed=knox_embed("✅ Servidor reiniciado", "El servidor está volviendo a estar online.", 0x00AA44))

@bot.command(name="players")
async def cmd_players(ctx):
    result = await rcon_command("players")
    embed = knox_embed("👥 Jugadores online", f"```{result}```" if result else "No hay jugadores conectados.")
    await ctx.send(embed=embed)

@bot.command(name="info")
async def cmd_info(ctx):
    embed = knox_embed(
        "📡 Knox Frontier RP — Info del servidor",
        f"**IP:** `{SERVER_PUBLIC_IP}`\n"
        f"**Puerto:** `{SERVER_PORT}`\n"
        f"**Build:** 42.19\n"
        f"**XP:** x2\n"
        f"**Modalidad:** Roleplay · PvP con motivo · PvE\n"
        f"**Discord:** discord.gg/AMk4hYWwM"
    )
    await ctx.send(embed=embed)

@bot.command(name="rules")
async def cmd_rules(ctx):
    embed = knox_embed(
        "📜 Reglas de Knox Frontier RP",
        "**1.** Respeta a todos los miembros.\n"
        "**2.** Prioriza el Roleplay — actúa según tu personaje.\n"
        "**3.** PvP permitido todos los días, pero con motivo dentro del RP.\n"
        "**4.** No Metagaming — no uses info de fuera del juego.\n"
        "**5.** No Exploits ni bugs.\n"
        "**6.** Respeta las bases — robos solo con contexto RP.\n"
        "**7.** Sin Combat Logging.\n"
        "**8.** Facciones y alianzas permitidas.\n"
        "**9.** Decisiones de admins son finales.\n\n"
        "✅ Roleplay · PvP con motivo · Comercio · Facciones\n"
        "❌ Metagaming · Exploits · Combat Logging · Griefing"
    )
    await ctx.send(embed=embed)

@bot.command(name="anuncio")
@is_staff()
async def cmd_anuncio(ctx, *, mensaje: str):
    if CHANNEL_ANUNCIOS == 0:
        await ctx.send("❌ Canal de anuncios no configurado.", delete_after=5)
        return
    channel = bot.get_channel(CHANNEL_ANUNCIOS)
    embed = knox_embed("📢 Anuncio — Knox Frontier RP", mensaje, 0xFFAA00)
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    await channel.send("@everyone", embed=embed)
    await ctx.message.add_reaction("✅")

@bot.command(name="raid")
@is_staff()
async def cmd_raid(ctx, *, detalles: str):
    if CHANNEL_ANUNCIOS == 0:
        return
    channel = bot.get_channel(CHANNEL_ANUNCIOS)
    embed = knox_embed(
        "⚔️ EVENTO DE RAID — Knox Frontier RP",
        f"**Detalles:**\n{detalles}\n\n"
        "Prepara tu facción. El apocalipsis no espera.",
        0xCC2222
    )
    await channel.send("@everyone", embed=embed)
    await ctx.message.add_reaction("✅")

@bot.command(name="say")
@is_staff()
async def cmd_say(ctx, *, mensaje: str):
    result = await rcon_command(f'servermsg "{mensaje}"')
    await ctx.send(embed=knox_embed("📣 Mensaje enviado al servidor", f"`{mensaje}`\n```{result}```", 0x00AA44))

@bot.command(name="ban")
@is_staff()
async def cmd_ban_pz(ctx, jugador: str, *, razon: str = "Sin razón especificada"):
    result = await rcon_command(f'banuser "{jugador}"')
    embed = knox_embed("🔨 Ban aplicado", f"Jugador: `{jugador}`\nRazón: {razon}\n```{result}```", 0xCC2222)
    await ctx.send(embed=embed)

@bot.command(name="kick")
@is_staff()
async def cmd_kick_pz(ctx, jugador: str, *, razon: str = "Sin razón especificada"):
    result = await rcon_command(f'kickuser "{jugador}"')
    embed = knox_embed("👢 Kick aplicado", f"Jugador: `{jugador}`\nRazón: {razon}\n```{result}```", 0xFFAA00)
    await ctx.send(embed=embed)

# ─────────────────────────────────────────
#   SLASH COMMANDS
# ─────────────────────────────────────────
@tree.command(name="info", description="Información del servidor Knox Frontier RP")
async def slash_info(interaction: discord.Interaction):
    embed = knox_embed(
        "📡 Knox Frontier RP — Info",
        f"**IP:** `{SERVER_PUBLIC_IP}`\n**Puerto:** `{SERVER_PORT}`\n"
        f"**Build:** 42.19 · **XP:** x2\n**Discord:** discord.gg/AMk4hYWwM"
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="rules", description="Ver las reglas del servidor")
async def slash_rules(interaction: discord.Interaction):
    embed = knox_embed(
        "📜 Reglas de Knox Frontier RP",
        "1. Respeta a todos.\n2. Prioriza el Roleplay.\n3. PvP con motivo.\n"
        "4. No Metagaming.\n5. No Exploits.\n6. Respeta las bases.\n"
        "7. Sin Combat Logging.\n8. Facciones permitidas.\n9. Admins son finales."
    )
    await interaction.response.send_message(embed=embed)

@tree.command(name="players", description="Ver jugadores online en el servidor")
async def slash_players(interaction: discord.Interaction):
    result = await rcon_command("players")
    embed = knox_embed("👥 Jugadores online", f"```{result}```" if result else "No hay jugadores conectados.")
    await interaction.response.send_message(embed=embed)

@tree.command(name="start", description="[STAFF] Iniciar el servidor PZ")
async def slash_start(interaction: discord.Interaction):
    if not is_staff_interaction(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return
    await interaction.response.send_message(embed=knox_embed("🚀 Iniciando servidor", "Arrancando Knox Frontier RP...", 0x00AA44))
    subprocess.Popen(PZ_EXE_PATH, shell=True)

@tree.command(name="stop", description="[STAFF] Detener el servidor PZ")
async def slash_stop(interaction: discord.Interaction):
    if not is_staff_interaction(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return
    result = await rcon_command("quit")
    await interaction.response.send_message(embed=knox_embed("🛑 Servidor detenido", f"```{result}```", 0xCC2222))

@tree.command(name="anuncio", description="[STAFF] Enviar un anuncio al canal de anuncios")
@app_commands.describe(mensaje="Mensaje del anuncio")
async def slash_anuncio(interaction: discord.Interaction, mensaje: str):
    if not is_staff_interaction(interaction):
        await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
        return
    if CHANNEL_ANUNCIOS == 0:
        await interaction.response.send_message("❌ Canal no configurado.", ephemeral=True)
        return
    channel = bot.get_channel(CHANNEL_ANUNCIOS)
    embed = knox_embed("📢 Anuncio — Knox Frontier RP", mensaje, 0xFFAA00)
    await channel.send("@everyone", embed=embed)
    await interaction.response.send_message("✅ Anuncio enviado.", ephemeral=True)

# ─────────────────────────────────────────
#   TASK — LOGS EN TIEMPO REAL
# ─────────────────────────────────────────
@tasks.loop(seconds=5)
async def watch_logs():
    if CHANNEL_LOGS == 0 or not os.path.exists(LOGS_PATH):
        return
    channel = bot.get_channel(CHANNEL_LOGS)
    if not channel:
        return

    for filename in os.listdir(LOGS_PATH):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(LOGS_PATH, filename)
        if filepath not in log_position:
            log_position[filepath] = os.path.getsize(filepath)
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(log_position[filepath])
                new_lines = f.readlines()
                log_position[filepath] = f.tell()
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                # Filtrar eventos importantes
                if any(k in line for k in ["joined", "disconnected", "died", "killed", "player", "Player", "LOG", "WARNING", "ERROR", "faction", "Faction"]):
                    color = 0xCC2222 if any(k in line for k in ["died", "killed", "ERROR", "WARNING"]) else 0x333333
                    embed = discord.Embed(description=f"```{line[:800]}```", color=color, timestamp=datetime.utcnow())
                    embed.set_footer(text=f"📋 {filename}")
                    await channel.send(embed=embed)
        except Exception:
            pass

# ─────────────────────────────────────────
#   ERROR HANDLER
# ─────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(embed=knox_embed("❌ Sin permisos", f"Necesitas el rol **{STAFF_ROLE_NAME}** para este comando.", 0xCC2222), delete_after=8)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=knox_embed("⚠️ Argumento faltante", f"Uso incorrecto del comando. Revisa `!help`.", 0xFFAA00), delete_after=8)

# ─────────────────────────────────────────
#   ARRANCAR
# ─────────────────────────────────────────
bot.run(TOKEN)
