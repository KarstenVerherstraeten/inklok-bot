import os
import time
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
    port = int(os.environ.get("PORT", 5000))
    
    # De bot-functie
    def run_bot():
        # Een extra korte slaapstand om Flask echt de tijd te geven
        time.sleep(10)
        try:
            print("🤖 Bot start nu op de achtergrond...")
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot Error: {e}")

    # Start de bot in een aparte thread
    # We gebruiken een daemon thread zodat hij stopt als de app stopt
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    # START FLASK ALS ALLEREERSTE
    print(f"🌐 Dashboard start op poort {port}...")
    # debug=False en use_reloader=False zijn VERPLICHT voor deze setup
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)