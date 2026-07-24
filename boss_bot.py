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
    "Jefe del Bosque Oscuro": ["12:00", "18:00", "00:00"],
    "Dragón de Fuego": ["14:00", "20:00", "02:00"],
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
WARNING_MINUTES = 5

# ═══════════════════════════════════════════════════════════
# CÓDIGO DEL BOT (NO EDITAR A PARTIR DE AQUÍ)
# ═══════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Guarda los próximos avisos para no repetirlos
sent_warnings = set()


def get_next_spawn_times():
    """Calcula los próximos spawns de cada jefe."""
    now = datetime.now(TIMEZONE)
    upcoming = []

    for boss_name, times in EVENT_SCHEDULE.items():
        for time_str in times:
            # Parsear la hora
            hour, minute = map(int, time_str.split(":"))
            spawn_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Si ya pasó hoy, es mañana
            if spawn_time < now:
                spawn_time += timedelta(days=1)

            upcoming.append({
                "boss": boss_name,
                "spawn_time": spawn_time,
                "warning_time": spawn_time - timedelta(minutes=WARNING_MINUTES)
            })

    # Ordenar por tiempo de aviso
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
    """Revisa cada 30 segundos si hay un jefe próximo a aparecer."""
    now = datetime.now(TIMEZONE)
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print(f"⚠️ No se encontró el canal con ID {CHANNEL_ID}")
        return

    upcoming_spawns = get_next_spawn_times()

    for spawn in upcoming_spawns:
        warning_time = spawn["warning_time"]
        spawn_time = spawn["spawn_time"]
        boss_name = spawn["boss"]

        # Crear ID único para este aviso (evita duplicados)
        warning_id = f"{boss_name}_{spawn_time.strftime('%Y-%m-%d_%H:%M')}"

        # Si ya pasó el tiempo de aviso y no hemos enviado aviso
        if now >= warning_time and now < spawn_time and warning_id not in sent_warnings:
            minutes_until = int((spawn_time - now).total_seconds() / 60)

            # Crear embed bonito
            embed = discord.Embed(
                title="⚔️ ¡ALERTA DE JEFE!",
                description=f"**{boss_name}** aparecerá en **{minutes_until} minutos**",
                color=0xFF4444
            )
            embed.add_field(
                name="🕐 Hora exacta del spawn",
                value=f"`{spawn_time.strftime('%H:%M')}`",
                inline=True
            )
            embed.add_field(
                name="📍 Mapa",
                value="Consulta el mapa del juego",
                inline=True
            )
            embed.set_footer(text="Orion2 Boss Bot • ¡Prepara tu equipo!")

            await channel.send(embed=embed)
            print(f"📢 Aviso enviado: {boss_name} a las {spawn_time.strftime('%H:%M')}")

            # Marcar como enviado
            sent_warnings.add(warning_id)

            # Limpiar avisos viejos (de hace más de 1 día)
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
        title="📅 Horarios de Jefes Configurados",
        color=0xAAFF44
    )

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
