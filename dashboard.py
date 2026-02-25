import os
import threading
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template

# Importeer de bot en token uit je bot.py
# Zorg dat bot.py in dezelfde map staat
from bot import bot, TOKEN 

app = Flask(__name__)

# Haal de database URL uit de Environment Variables van Render
DB_URI = os.getenv("DATABASE_URL")

def get_db_dashboard():
    # Connectie met Supabase (PostgreSQL)
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    try:
        conn = get_db_dashboard()
        cur = conn.cursor()
        
        # 1. LOGBOEK: Laatste 50 sessies
        cur.execute('''
    SELECT user_id, user_name, start_time::text, end_time::text, duration 
    FROM dienst 
    WHERE end_time IS NOT NULL 
    ORDER BY start_time DESC 
    LIMIT 50
''')
        diensten = cur.fetchall()
        
        # 2. TOP LIJST: Totaal uren per persoon
        cur.execute('''
            SELECT user_name, COALESCE(SUM(duration)/60, 0) as totaal_uren, COUNT(*) as sessies 
            FROM dienst 
            WHERE duration IS NOT NULL
            GROUP BY user_name
            ORDER BY totaal_uren DESC
        ''')
        stats = cur.fetchall()
        
        # 3. ACTIEVE KRACHTEN: Wie is er nu ingeklokt?
        cur.execute('''
    SELECT user_name, start_time::text 
    FROM dienst 
    WHERE end_time IS NULL
''')
        actieve_leden = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('index.html', 
                               diensten=diensten, 
                               stats=stats, 
                               actieve_count=len(actieve_leden), 
                               actieve_leden=actieve_leden)
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return f"Database Error. Check logs.", 500

# Functie om de bot te starten met een kleine vertraging
def start_discord_bot():
    # We wachten 10 seconden zodat Flask alle tijd heeft om de poort te claimen
    time.sleep(10)
    print("🤖 Discord bot thread: Poging tot inloggen...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Bot Error: {e}")

if __name__ == '__main__':
    # 1. Start de bot thread (daemon=True zorgt dat hij stopt als de app stopt)
    print("🧵 Bot thread voorbereiden...")
    t = threading.Thread(target=start_discord_bot, daemon=True)
    t.start()
    
    # 2. Bepaal de poort (Render gebruikt standaard 10000 of de PORT env)
    port = int(os.environ.get("PORT", 10000))
    
    # 3. START FLASK
    # use_reloader=False is cruciaal om te voorkomen dat de bot twee keer start!
    print(f"🌐 Dashboard start op poort {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)