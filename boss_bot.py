import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import pytz
import asyncio

# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN - EDITAR ESTOS VALORES
# ═══════════════════════════════════════════════════════════

import os
TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = 1530256665616842792   # ← ID del canal donde enviará los avisos

# Zona horaria del juego (ajústala según el servidor de Orion2)
TIMEZONE = pytz.timezone("Europe/Berlin")  # Cambia a tu zona

# ═══════════════════════════════════════════════════════════
# HORARIOS DE JEFES - CONFIGURA LOS JEFES DE ORION2 AQUÍ
# ═══════════════════════════════════════════════════════════
# Formato: "Nombre del Jefe": ["HH:MM", "HH:MM", ...]
# Puedes poner múltiples horarios por jefe

EVENT_SCHEDULE = {
    # ═══════ JEFES ═══════
    "General Yonghan Gruta 2": ["22:30", "00:00", "01:30","03:00", "04:30", "06:00","07:30", "09:00", "10:30","12:00", "13:30", "15:00","16:30", "18:00", "19:30","21:00"],
    "Magic Golem Gruta 1": ["22:30", "00:00", "01:30","03:00", "04:30", "06:00","07:30", "09:00", "10:30","12:00", "13:30", "15:00","16:30", "18:00", "19:30","21:00"],
    "Golem de Piedra": ["10:00", "16:00", "22:00"],
    "Espectro del Abismo": ["08:00", "15:00", "21:00"],
    "Rey Orco": ["11:00", "17:00", "23:00"],
    
    # ═══════ METINES ═══════
    "Metin de Fuego": ["09:00", "15:00", "21:00"],
    "Metin de Hielo": ["10:00", "16:00", "22:00"],
    "Metin del Trueno": ["11:00", "17:00", "23:00"],
    
    # ═══════ EVENTOS ESPECIALES ═══════
    "Guerra del Reino": ["20:00"],
    "Torneo PvP": ["19:00"],
    "Doble Experiencia": ["16:00"],
}

# Minutos antes del spawn para enviar el aviso
WARNING_MINUTES = [10, 5, 1]  # Avisos a 10, 5 y 1 minuto antes

# ═══════════════════════════════════════════════════════════
# CÓDIGO DEL BOT (NO EDITAR A PARTIR DE AQUÍ)
# ═══════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Guarda los próximos avisos para no repetirlos
sent_warnings = set()


def get_next_spawn_times():
    """Calcula los próximos spawns de cada evento."""
    now = datetime.now(TIMEZONE)
    upcoming = []

    for event_name, times in EVENT_SCHEDULE.items():
        for time_str in times:
            hour, minute = map(int, time_str.split(":"))
            spawn_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if spawn_time < now:
                spawn_time += timedelta(days=1)

            # Crear un aviso por cada tiempo de warning
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
    print("⏰ Iniciando monitoreo de jefes...")

    # Iniciar la tarea de monitoreo
    check_bosses.start()


@tasks.loop(seconds=30)
async def check_bosses():
    """Revisa cada 30 segundos si hay un evento próximo a aparecer."""
    now = datetime.now(TIMEZONE)
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        return

    upcoming_spawns = get_next_spawn_times()

    for spawn in upcoming_spawns:
        warning_time = spawn["warning_time"]
        spawn_time = spawn["spawn_time"]
        event_name = spawn["event"]
        warning_min = spawn["warning_min"]

        # Crear ID único para este aviso específico (incluye los minutos de aviso)
        warning_id = f"{event_name}_{spawn_time.strftime('%Y-%m-%d_%H:%M')}_{warning_min}min"

        if now >= warning_time and now < spawn_time and warning_id not in sent_warnings:
            minutes_until = int((spawn_time - now).total_seconds() / 60)

            # Color según tipo de evento
            if "Jefe" in event_name or "General" in event_name:
                color = 0xFF0000  # Rojo para jefes
                emoji = "⚔️"
            elif "Metin" in event_name:
                color = 0xFFA500  # Naranja para metines
                emoji = "💎"
            else:
                color = 0x00FF00  # Verde para eventos
                emoji = "🎉"

            # Emoji según tiempo de aviso
            if warning_min == 15:
                time_emoji = "⏳"
            elif warning_min == 5:
                time_emoji = "🔔"
            else:
                time_emoji = "🚨"

            embed = discord.Embed(
                title=f"{time_emoji} ¡ALERTA DE EVENTO! {time_emoji}",
                description=f"{emoji} **{event_name}** aparecerá en **{minutes_until} minutos**",
                color=color
            )
            embed.add_field(
                name="🕐 Hora exacta",
                value=f"`{spawn_time.strftime('%H:%M')}`",
                inline=True
            )
            embed.add_field(
                name="⏰ Aviso",
                value=f"`{warning_min} min antes`",
                inline=True
            )
            embed.set_footer(text="Orion2 Boss Bot • ¡Prepara tu equipo!")

            await channel.send("@everyone", embed=embed)
            sent_warnings.add(warning_id)
            cleanup_old_warnings()

    # Limpiar sent_warnings de avisos que ya pasaron hace tiempo
    cleanup_old_warnings()


def cleanup_old_warnings():
    """Elimina avisos antiguos para liberar memoria."""
    now = datetime.now(TIMEZONE)
    to_remove = set()

    for warning_id in sent_warnings:
        # Extraer la fecha del ID
        try:
            parts = warning_id.rsplit("_", 1)
            date_str = parts[1]
            warning_date = datetime.strptime(date_str, "%H:%M")
            warning_date = now.replace(hour=warning_date.hour, minute=warning_date.minute)

            if now - warning_date > timedelta(days=1):
                to_remove.add(warning_id)
        except:
            pass

    sent_warnings.difference_update(to_remove)


# ═══════════════════════════════════════════════════════════
# COMANDOS SLASH
# ═══════════════════════════════════════════════════════════

@bot.tree.command(name="bosses", description="Muestra los próximos jefes que aparecerán")
async def bosses_command(interaction: discord.Interaction):
    upcoming = get_next_spawn_times()
    now = datetime.now(TIMEZONE)

    embed = discord.Embed(
        title="📋 Próximos Jefes",
        description="Lista de jefes ordenados por hora de aparición",
        color=0x44AAFF
    )

    # Mostrar los próximos 10 spawns
    for i, spawn in enumerate(upcoming[:10]):
        time_left = spawn["spawn_time"] - now
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)

        time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        embed.add_field(
            name=f"⚔️ {spawn['boss']}",
            value=f"🕐 `{spawn['spawn_time'].strftime('%H:%M')}` (en {time_str})",
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="agregar_jefe", description="Agrega un nuevo jefe al horario")
@discord.app_commands.describe(
    nombre="Nombre del jefe",
    hora="Hora de spawn (formato HH:MM, 24h)"
)
async def add_boss_command(interaction: discord.Interaction, nombre: str, hora: str):
    try:
        # Validar formato de hora
        datetime.strptime(hora, "%H:%M")

        if nombre not in EVENT_SCHEDULE:
            EVENT_SCHEDULE[nombre] = []

        if hora not in EVENT_SCHEDULE[nombre]:
            EVENT_SCHEDULE[nombre].append(hora)
            await interaction.response.send_message(
                f"✅ Jefe **{nombre}** agregado a las `{hora}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Ese horario ya existe para **{nombre}**",
                ephemeral=True
            )
    except ValueError:
        await interaction.response.send_message(
            "❌ Formato de hora inválido. Usa `HH:MM` (ej: `14:30`)",
            ephemeral=True
        )


@bot.tree.command(name="eliminar_jefe", description="Elimina un jefe del horario")
@discord.app_commands.describe(nombre="Nombre del jefe a eliminar")
async def remove_boss_command(interaction: discord.Interaction, nombre: str):
    if nombre in EVENT_SCHEDULE:
        del EVENT_SCHEDULE[nombre]
        await interaction.response.send_message(
            f"🗑️ Jefe **{nombre}** eliminado del horario",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ No se encontró el jefe **{nombre}**",
            ephemeral=True
        )


@bot.tree.command(name="horarios", description="Muestra todos los horarios configurados")
async def schedule_command(interaction: discord.Interaction):
    embed = discord.Embed(
    title="⏰ ALERTA DE EVENTO ⏰",
    description=f"""
    ━━━━━━━━━━━━━━━━━━━━━━━
    ⚔️ **{boss_name}**
    
    🕐 Aparece en: `{spawn_time.strftime('%H:%M')}`
    ⏳ Tiempo restante: **{minutes_until} minutos**
    
    📍 Prepara tu equipo y únete al grupo
    ━━━━━━━━━━━━━━━━━━━━━━━
    """,
    color=0xFF4444
)
embed.set_footer(text="Orion2 Boss Bot • ¡No te lo pierdas!")

    for boss, times in EVENT_SCHEDULE.items():
        times_str = ", ".join([f"`{t}`" for t in sorted(times)])
        embed.add_field(name=f"⚔️ {boss}", value=times_str, inline=False)

    await interaction.response.send_message(embed=embed)


# Sincronizar comandos slash al iniciar
@bot.event
async def setup_hook():
    await bot.tree.sync()
    print("🔄 Comandos slash sincronizados")


# ═══════════════════════════════════════════════════════════
# EJECUTAR BOT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    bot.run(TOKEN)
