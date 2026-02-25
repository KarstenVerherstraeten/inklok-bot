import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template
from bot import bot, TOKEN  # We importeren de bot en token uit je bot.py

app = Flask(__name__)

# Haal de database URL uit de Environment Variables van Render
DB_URI = os.getenv("DATABASE_URL")

def get_db_dashboard():
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    try:
        conn = get_db_dashboard()
        cur = conn.cursor()
        
        # 1. LOGBOEK
        cur.execute('''
            SELECT user_id, user_name, start_time, end_time, duration 
            FROM dienst 
            WHERE end_time IS NOT NULL 
            ORDER BY start_time DESC 
            LIMIT 50
        ''')
        diensten = cur.fetchall()
        
        # 2. TOP LIJST (Bonus)
        cur.execute('''
            SELECT user_name, COALESCE(SUM(duration)/60, 0) as totaal_uren, COUNT(*) as sessies 
            FROM dienst 
            WHERE duration IS NOT NULL
            GROUP BY user_name
            ORDER BY totaal_uren DESC
        ''')
        stats = cur.fetchall()
        
        # 3. ACTIEVE KRACHTEN
        cur.execute('''
            SELECT user_name, start_time 
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
        return f"Database Error: {e}", 500

if __name__ == '__main__':
    # Haal de poort op die Render ons toewijst
    port = int(os.environ.get("PORT", 5000))
    
    # We definiëren een functie om de bot te starten
    def run_bot():
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot Error: {e}")

    # Start de bot in een achtergrond-thread
    print("🤖 Bot thread wordt voorbereid...")
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask DIRECT (Render ziet dan meteen de poort)
    print(f"🌐 Dashboard opstarten op poort {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)