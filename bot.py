import discord
from discord import app_commands
from discord.ext import commands
import psycopg2  # Voor Supabase
from datetime import datetime, timedelta
import ssl
import certifi

# --- CONFIGURATIE ---
# BELANGRIJK: Vervang 'xxxx' door jouw unieke Supabase ID
DB_URI = "postgresql://postgres:UGLhFvr04hluHH5H@db.qujvvlpguvmuypsplmmd.supabase.co:5432/postgres"
TOKEN = 'MTQ3NjIyODcyMTQxMjE0NTI4Nw.Gl_7to.UOg7o15loxjz6_lVlcm2tUw4E_1PS6ftjMwBh8'

# --- DATABASE SETUP ---
def get_db_connection():
    return psycopg2.connect(DB_URI)

# --- BOT SETUP ---
class ANWBBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Bot is ingelogd als {self.user}")
        print(f"✅ Slash commando's gesynchroniseerd met Supabase")

bot = ANWBBot()

# --- HELPER FUNCTIES ---
def get_monthly_hours(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    # PostgreSQL syntax voor 'afgelopen 30 dagen'
    query = """
        SELECT SUM(duration) FROM dienst 
        WHERE user_id = %s AND start_time > NOW() - INTERVAL '30 days'
    """
    c.execute(query, (user_id,))
    res = c.fetchone()[0]
    conn.close()
    return round(res / 60, 2) if res else 0

# --- COMMANDS ---

@bot.tree.command(name="indienst", description="Start je wegenwachter dienst")
async def indienst(interaction: discord.Interaction):
    user_id = interaction.user.id
    user_name = interaction.user.display_name
    now_dt = datetime.now()
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check of de gebruiker al in dienst is
    c.execute("SELECT id FROM dienst WHERE user_id = %s AND end_time IS NULL", (user_id,))
    if c.fetchone():
        await interaction.response.send_message("❌ Je bent al in dienst!", ephemeral=True)
        conn.close()
        return

    c.execute("INSERT INTO dienst (user_id, user_name, start_time) VALUES (%s, %s, %s)", 
              (user_id, user_name, now_dt))
    conn.commit()
    conn.close()

    maand_uren = get_monthly_hours(user_id)
    
    embed = discord.Embed(title="🛠️ Wegenwachter - Dienst Gestart", color=discord.Color.green())
    embed.add_field(name="Medewerker:", value=user_name, inline=True)
    embed.add_field(name="Inkloktijd:", value=now_dt.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    embed.add_field(name="Inzet afgelopen 30 dagen:", value=f"{maand_uren} uur", inline=False)
    embed.set_footer(text="Succes met je patrouille!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="uitdienst", description="Stop je wegenwachter dienst")
async def uitdienst(interaction: discord.Interaction):
    user_id = interaction.user.id
    user_name = interaction.user.display_name
    now_dt = datetime.now()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, start_time FROM dienst WHERE user_id = %s AND end_time IS NULL", (user_id,))
    result = c.fetchone()

    if not result:
        await interaction.response.send_message("❌ Je bent momenteel niet in dienst!", ephemeral=True)
        conn.close()
        return

    row_id, start_dt = result
    
    # Bereken verschil in minuten
    diff = (now_dt - start_dt).total_seconds() / 60
    
    c.execute("UPDATE dienst SET end_time = %s, duration = %s WHERE id = %s", (now_dt, diff, row_id))
    conn.commit()
    conn.close()

    maand_uren = get_monthly_hours(user_id)

    embed = discord.Embed(title="🏁 Wegenwachter - Dienst Beëindigd", color=discord.Color.red())
    embed.add_field(name="Medewerker:", value=user_name, inline=True)
    embed.add_field(name="Sessie duur:", value=f"{round(diff, 1)} minuten", inline=True)
    embed.add_field(name="Totaal 30 dagen:", value=f"{maand_uren} uur", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- RUN BOT ---
bot.run(TOKEN)