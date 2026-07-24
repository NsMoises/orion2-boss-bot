import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# =========================================================
# CONFIGURACIÓN
# =========================================================

TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = 1530256665616842792
TIMEZONE = pytz.timezone("Europe/Berlin")

# =========================================================
# HORARIOS DE EVENTOS
# =========================================================

EVENT_SCHEDULE = {
    # ======= SOLDADOS DE LA DINASTÍA =======
    "General Yonghan Gruta 2": ["22:30", "00:00", "01:30", "03:00", "04:30", "06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"],
    "Golem Magico Gruta 1": ["22:30", "00:00", "01:30", "03:00", "04:30", "06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"],
    "Golem de Piedra": ["10:00", "16:00", "22:00"],
    "Espectro del Abismo": ["08:00", "15:00", "21:00"],
    "Rey Orco": ["11:00", "17:00", "23:00"],

    # ======= METINES SAGRADOS =======
    "Metin de Gruta 1": ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"],
    "Metin de Hielo": ["10:00", "16:00", "22:00"],
    "Metin del Trueno": ["11:00", "17:00", "23:00"],

    # ======= GRANDES GUERRAS =======
    "Bruja de Hielo Gruta 1": ["11:10", "17:10", "20:10", "23:10"],
    "Rey Wubba Map 90": ["11:40", "17:40", "20:40", "22:40"],
    "Azrael Infernal": ["09:00", "19:00", "22:00"],
}

WARNING_MINUTES = [10, 5, 1]

# =========================================================
# CONFIGURACIÓN VISUAL — DINASTÍA CHINA
# =========================================================

EVENT_CONFIG = {
    "General Yonghan Gruta 2": {"rank": "🏯 MARISCAL", "color": 0xC41E3A, "banner": "🐉"},
    "Golem Magico Gruta 1":    {"rank": "🧙 MAGO", "color": 0x9932CC, "banner": "🔮"},
    "Golem de Piedra":         {"rank": "🗿 GUARDIÁN", "color": 0x8B7355, "banner": "⛰️"},
    "Espectro del Abismo":     {"rank": "👻 ESPECTRO", "color": 0x4A0080, "banner": "🌑"},
    "Rey Orco":                {"rank": "👹 SEÑOR", "color": 0x228B22, "banner": "🪓"},
    "Metin de Gruta 1":        {"rank": "💎 METIN", "color": 0xFF6347, "banner": "☄️"},
    "Metin de Hielo":          {"rank": "❄️ METIN", "color": 0x00BFFF, "banner": "🧊"},
    "Metin del Trueno":        {"rank": "⚡ METIN", "color": 0xFFD700, "banner": "🌩️"},
    "Bruja de Hielo Gruta 1":  {"rank": "🧙 BRUJA", "color": 0x00CED1, "banner": "❄️"},
    "Rey Wubba Map 90":        {"rank": "👑 REY", "color": 0xFFD700, "banner": "👑"},
    "Azrael Infernal":         {"rank": "😈 AZRAEL", "color": 0x8B0000, "banner": "🔥"},
}

WARNING_STYLES = {
    10: {
        "seal": "◈◈◈",
        "call": "Los exploradores avistan movimiento en el horizonte...",
        "mood": "🟢",
        "mention": False,
    },
    5: {
        "seal": "◈◈◈ ◈◈◈",
        "call": "¡Los tambores de guerra retumban! ¡A las armas!",
        "mood": "🟡",
        "mention": True,
    },
    1: {
        "seal": "◈◈◈ ◈◈◈ ◈◈◈",
        "call": "¡EL ENEMIGO ESTÁ A LAS PUERTAS! ¡FORMACIÓN!",
        "mood": "🔴",
        "mention": True,
    },
}

# =========================================================
# CÓDIGO DEL BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

sent_warnings = set()


def get_event_config(event_name):
    return EVENT_CONFIG.get(event_name, {"rank": "📌 SOLDADO", "color": 0x7289DA, "banner": "📍"})


def get_next_spawn_times():
    now = datetime.now(TIMEZONE)
    upcoming = []

    for event_name, times in EVENT_SCHEDULE.items():
        for time_str in times:
            hour, minute = map(int, time_str.split(":"))
            spawn_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if spawn_time < now:
                spawn_time += timedelta(days=1)

            for warning_min in WARNING_MINUTES:
                warning_time = spawn_time - timedelta(minutes=warning_min)
                upcoming.append({
                    "event": event_name,
                    "spawn_time": spawn_time,
                    "warning_time": warning_time,
                    "warning_min": warning_min
                })

    upcoming.sort(key=lambda x: x["warning_time"])
    return upcoming


@bot.event
async def on_ready():
    print(f"🏯 Bot de la Dinastía conectado: {bot.user}")
    check_events.start()
    daily_cleanup.start()


@tasks.loop(seconds=30)
async def check_events():
    now = datetime.now(TIMEZONE)
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        return

    upcoming = get_next_spawn_times()

    for spawn in upcoming:
        warning_time = spawn["warning_time"]
        spawn_time = spawn["spawn_time"]
        event_name = spawn["event"]
        warning_min = spawn["warning_min"]

        warning_id = f"{event_name}_{spawn_time.strftime('%Y-%m-%d_%H:%M')}_{warning_min}min"

        if now >= warning_time and now < spawn_time and warning_id not in sent_warnings:
            minutes_until = int((spawn_time - now).total_seconds() / 60)

            cfg = get_event_config(event_name)
            warn = WARNING_STYLES[warning_min]

            embed = discord.Embed(
                title=f"{warn['seal']}",
                description=f"""
{cfg['banner']} **{cfg['rank']}** {cfg['banner']}

> *"{warn['call']}"*

━━━━━━━━━━━━━━━━━━━━━━━
**{event_name}**
━━━━━━━━━━━━━━━━━━━━━━━

⏳ **Marcha en:** `{minutes_until} minutos`
🕐 **Hora del encuentro:** `{spawn_time.strftime('%H:%M')}`
🌍 **Zona:** Europa/Berlín

{warn['mood']} Urgencia: `{warning_min} minutos restantes`
                """,
                color=cfg['color']
            )

            embed.set_footer(text="🏯 DinastíaL7 • ¡Por el honor del emperador!")

            if warn['mention']:
                await channel.send("@everyone", embed=embed)
            else:
                await channel.send(embed=embed)

            sent_warnings.add(warning_id)
            cleanup_old_warnings()


def cleanup_old_warnings():
    now = datetime.now(TIMEZONE)
    to_remove = set()
    for warning_id in sent_warnings:
        try:
            parts = warning_id.rsplit("_", 2)
            date_str = parts[1]
            warning_date = datetime.strptime(date_str, "%H:%M")
            warning_date = now.replace(hour=warning_date.hour, minute=warning_date.minute)
            if now - warning_date > timedelta(days=1):
                to_remove.add(warning_id)
        except:
            pass
    sent_warnings.difference_update(to_remove)


# =========================================================
# LIMPIEZA AUTOMÁTICA DIARIA A LAS 00:00
# =========================================================

@tasks.loop(minutes=1)
async def daily_cleanup():
    now = datetime.now(TIMEZONE)

    if now.hour == 0 and now.minute == 0:
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            return

        ayer = now - timedelta(days=1)
        fecha_ayer_str = ayer.strftime('%Y-%m-%d')

        def es_mensaje_del_bot_de_ayer(m):
            if m.author.id != bot.user.id:
                return False
            msg_fecha = m.created_at.astimezone(TIMEZONE).strftime('%Y-%m-%d')
            return msg_fecha == fecha_ayer_str

        try:
            eliminados = await channel.purge(limit=500, check=es_mensaje_del_bot_de_ayer)
            print(f"🗑️ Limpieza diaria: {len(eliminados)} mensajes del {fecha_ayer_str} eliminados")

            embed = discord.Embed(
                title="🧹 LIMPIEZA DIARIA COMPLETADA",
                description=f"Se han purgado **{len(eliminados)}** mensajes del día anterior.\n\n*El canal está listo para nuevas batallas.*",
                color=0x2ECC71
            )
            embed.set_footer(text="🏯 DinastíaL7 • Limpieza automática")
            await channel.send(embed=embed)

        except Exception as e:
            print(f"Error en limpieza diaria: {e}")

        await asyncio.sleep(120)


# =========================================================
# COMANDOS SLASH
# =========================================================

@bot.tree.command(name="bosses", description="Próximas batallas de la Dinastía")
async def bosses_command(interaction: discord.Interaction):
    upcoming = get_next_spawn_times()
    now = datetime.now(TIMEZONE)

    embed = discord.Embed(
        title="🏯 ORDEN DE BATALLA 🏯",
        description="*Los generales han dispuesto las próximas campañas*",
        color=0x8B0000
    )

    shown = set()
    for spawn in upcoming:
        event_id = f"{spawn['event']}_{spawn['spawn_time'].strftime('%H:%M')}"
        if event_id in shown:
            continue
        shown.add(event_id)

        cfg = get_event_config(spawn["event"])
        time_left = spawn["spawn_time"] - now
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        embed.add_field(
            name=f"{cfg['banner']} {cfg['rank']} — {spawn['event']}",
            value=f"🕐 `{spawn['spawn_time'].strftime('%H:%M')}` *(en {time_str})*",
            inline=False
        )

        if len(shown) >= 15:
            break

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="agregar_evento", description="Añadir nuevo soldado al ejército")
@discord.app_commands.describe(nombre="Nombre del guerrero", hora="Hora de aparición HH:MM")
async def add_event_command(interaction: discord.Interaction, nombre: str, hora: str):
    try:
        datetime.strptime(hora, "%H:%M")
        if nombre not in EVENT_SCHEDULE:
            EVENT_SCHEDULE[nombre] = []
        if hora not in EVENT_SCHEDULE[nombre]:
            EVENT_SCHEDULE[nombre].append(hora)
            await interaction.response.send_message(f"🏯 **{nombre}** se une al ejército a las `{hora}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ Ese horario ya está en los registros", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ Formato inválido. Usa `HH:MM`", ephemeral=True)


@bot.tree.command(name="eliminar_evento", description="Retirar soldado del ejército")
async def remove_event_command(interaction: discord.Interaction, nombre: str):
    if nombre in EVENT_SCHEDULE:
        del EVENT_SCHEDULE[nombre]
        await interaction.response.send_message(f"🗑️ **{nombre}** ha sido retirado del servicio", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No se encuentra en los registros", ephemeral=True)


@bot.tree.command(name="horarios", description="Registros completos del ejército")
async def schedule_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 ROLLO DE HONOR 📜",
        description="*Todos los soldados y sus horas de guardia*",
        color=0xDAA520
    )

    for event_name, times in EVENT_SCHEDULE.items():
        cfg = get_event_config(event_name)
        times_str = "  ".join([f"`{t}`" for t in sorted(times)])
        embed.add_field(
            name=f"{cfg['banner']} {cfg['rank']} | {event_name}",
            value=times_str,
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="limpiar", description="Borra los mensajes del bot en este canal (solo admins)")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.describe(cantidad="Cantidad de mensajes a revisar (máx 100)")
async def limpiar_command(interaction: discord.Interaction, cantidad: int = 100):
    await interaction.response.defer(ephemeral=True)

    if cantidad > 100:
        cantidad = 100

    def es_mensaje_del_bot(m):
        return m.author.id == bot.user.id

    eliminados = await interaction.channel.purge(limit=cantidad, check=es_mensaje_del_bot)

    await interaction.followup.send(
        f"🗑️ **{len(eliminados)}** mensajes del bot han sido ejecutados.",
        ephemeral=True
    )


@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("🥁 Comandos de la Dinastía sincronizados")


if __name__ == "__main__":
    bot.run(TOKEN)
