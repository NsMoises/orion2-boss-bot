import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# =========================================================
# CONFIGURACION
# =========================================================

TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = 1530256665616842792
TIMEZONE = pytz.timezone("Europe/Berlin")

# =========================================================
# HORARIOS DE EVENTOS
# =========================================================

EVENT_SCHEDULE = {
    # ======= JEFES =======
    "General Yonghan Gruta 2": ["22:30", "00:00", "01:30", "03:00", "04:30", "06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"],
    "Golem Magico Gruta 1": ["22:30", "00:00", "01:30", "03:00", "04:30", "06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"],
    "Golem de Piedra": ["10:00", "16:00", "22:00"],
    "Espectro del Abismo": ["08:00", "15:00", "21:00"],
    "Rey Orco": ["11:00", "17:00", "23:00"],

    # ======= METINES =======
    "Metin de Gruta 1": ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"],
    "Metin de Hielo": ["10:00", "16:00", "22:00"],
    "Metin del Trueno": ["11:00", "17:00", "23:00"],

    # ======= EVENTOS ESPECIALES =======
    "Guerra del Reino": ["20:00"],
    "Torneo PvP": ["19:00"],
    "Doble Experiencia": ["16:00"],
}

WARNING_MINUTES = [15, 5, 1]

# =========================================================
# CONFIGURACION VISUAL
# =========================================================

EVENT_CONFIG = {
    # Jefes
    "General Yonghan Gruta 2": {"emoji": "👑", "color": 0xFFD700, "image": "https://i.imgur.com/boss_crown.png"},
    "Dragon de Fuego": {"emoji": "🐉", "color": 0xFF4500, "image": None},
    "Golem de Piedra": {"emoji": "🗿", "color": 0x8B4513, "image": None},
    "Espectro del Abismo": {"emoji": "👻", "color": 0x4B0082, "image": None},
    "Rey Orco": {"emoji": "👹", "color": 0x228B22, "image": None},

    # Metines
    "Metin de Fuego": {"emoji": "🔥", "color": 0xFF6347, "image": None},
    "Metin de Hielo": {"emoji": "❄️", "color": 0x00BFFF, "image": None},
    "Metin del Trueno": {"emoji": "⚡", "color": 0xFFD700, "image": None},

    # Eventos
    "Guerra del Reino": {"emoji": "⚔️", "color": 0xDC143C, "image": None},
    "Torneo PvP": {"emoji": "🏆", "color": 0xFFA500, "image": None},
    "Doble Experiencia": {"emoji": "✨", "color": 0x9370DB, "image": None},
}

WARNING_CONFIG = {
    15: {"emoji": "⏳", "title": "📢 PRE-ALERTA", "mention": False},
    5: {"emoji": "🔔", "title": "🚨 ALERTA", "mention": True},
    1: {"emoji": "🚨", "title": "🔥 ULTIMO MINUTO", "mention": True},
}

# =========================================================
# CODIGO DEL BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

sent_warnings = set()


def get_event_config(event_name):
    return EVENT_CONFIG.get(event_name, {"emoji": "📌", "color": 0x7289DA, "image": None})


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
    print(f"✅ Bot conectado como: {bot.user}")
    print(f"📡 Canal objetivo: {CHANNEL_ID}")
    check_events.start()


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

            config = get_event_config(event_name)
            warn_config = WARNING_CONFIG.get(warning_min, WARNING_CONFIG[5])

            emoji = config["emoji"]
            color = config["color"]

            # Mensaje segun tiempo
            if warning_min == 15:
                desc = f"**{event_name}** aparecera en **15 minutos**\nPrepara tu equipo!"
            elif warning_min == 5:
                desc = f"**{event_name}** en **5 minutos!**\n🎯 Posicionate ya!"
            else:
                desc = f"**{event_name}** en **1 minuto!**\n🏃 Corre ya!"

            embed = discord.Embed(
                title=f"{warn_config['emoji']} {warn_config['title']} {warn_config['emoji']}",
                description=f"""
{emoji} {emoji} {emoji} {emoji} {emoji}

{desc}

⏰ **Hora exacta:** `{spawn_time.strftime('%H:%M')}`
📍 **Zona horaria:** Europa/Berlin
                """,
                color=color
            )

            # Barra visual de urgencia
            if warning_min == 15:
                embed.add_field(name="Urgencia", value="🟢🟢🟢🟢🟢", inline=False)
            elif warning_min == 5:
                embed.add_field(name="Urgencia", value="🟡🟡🟡🟡⚪", inline=False)
            else:
                embed.add_field(name="Urgencia", value="🔴🔴🔴🔴🔴", inline=False)

            embed.set_footer(text="Orion2 Boss Bot • ¡No te lo pierdas!")

            # Mencion @everyone solo en alertas importantes
            if warn_config["mention"]:
                await channel.send("@everyone", embed=embed)
            else:
                await channel.send(embed=embed)

            print(f"📢 Aviso: {event_name} - {warning_min}min")
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


@bot.tree.command(name="bosses", description="Muestra los proximos eventos")
async def bosses_command(interaction: discord.Interaction):
    upcoming = get_next_spawn_times()
    now = datetime.now(TIMEZONE)

    embed = discord.Embed(
        title="📋 PROXIMOS EVENTOS",
        description="Lista completa de eventos ordenados por tiempo",
        color=0x5865F2
    )

    shown = set()
    for spawn in upcoming:
        event_id = f"{spawn['event']}_{spawn['spawn_time'].strftime('%H:%M')}"
        if event_id in shown:
            continue
        shown.add(event_id)

        config = get_event_config(spawn["event"])
        time_left = spawn["spawn_time"] - now
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        embed.add_field(
            name=f"{config['emoji']} {spawn['event']}",
            value=f"🕐 `{spawn['spawn_time'].strftime('%H:%M')}` (en {time_str})",
            inline=False
        )

        if len(shown) >= 15:
            break

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="agregar_evento", description="Agrega un nuevo evento")
@discord.app_commands.describe(nombre="Nombre del evento", hora="Hora HH:MM")
async def add_event_command(interaction: discord.Interaction, nombre: str, hora: str):
    try:
        datetime.strptime(hora, "%H:%M")
        if nombre not in EVENT_SCHEDULE:
            EVENT_SCHEDULE[nombre] = []
        if hora not in EVENT_SCHEDULE[nombre]:
            EVENT_SCHEDULE[nombre].append(hora)
            await interaction.response.send_message(f"✅ **{nombre}** agregado a las `{hora}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ Horario ya existe", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ Formato invalido. Usa `HH:MM`", ephemeral=True)


@bot.tree.command(name="eliminar_evento", description="Elimina un evento")
async def remove_event_command(interaction: discord.Interaction, nombre: str):
    if nombre in EVENT_SCHEDULE:
        del EVENT_SCHEDULE[nombre]
        await interaction.response.send_message(f"🗑️ **{nombre}** eliminado", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No encontrado", ephemeral=True)


@bot.tree.command(name="horarios", description="Muestra todos los horarios")
async def schedule_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📅 HORARIOS COMPLETOS", color=0xAAFF44)

    for event_name, times in EVENT_SCHEDULE.items():
        config = get_event_config(event_name)
        times_str = ", ".join([f"`{t}`" for t in sorted(times)])
        embed.add_field(name=f"{config['emoji']} {event_name}", value=times_str, inline=False)

    await interaction.response.send_message(embed=embed)


@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("🔄 Comandos slash sincronizados")


if __name__ == "__main__":
    bot.run(TOKEN)
