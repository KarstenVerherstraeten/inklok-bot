import os

from flask import Flask, render_template
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Jouw Supabase URI
DB_URI = os.getenv("DATABASE_URL")

def get_db_dashboard():
    # RealDictCursor zorgt ervoor dat we row['kolomnaam'] kunnen gebruiken in de HTML
    return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    conn = get_db_dashboard()
    cur = conn.cursor()
    
    # 1. LOGBOEK: Laatste 50 afgeronde diensten
    cur.execute('''
        SELECT user_id, user_name, start_time, end_time, duration 
        FROM dienst 
        WHERE end_time IS NOT NULL 
        ORDER BY start_time DESC 
        LIMIT 50
    ''')
    diensten = cur.fetchall()
    
    # 2. TOP LIJST (Bonus): Totaal uren per persoon
    # IFNULL is nu COALESCE voor PostgreSQL
    cur.execute('''
        SELECT user_name, COALESCE(SUM(duration)/60, 0) as totaal_uren, COUNT(*) as sessies 
        FROM dienst 
        WHERE duration IS NOT NULL
        GROUP BY user_name
        ORDER BY totaal_uren DESC
    ''')
    stats = cur.fetchall()
    
    # 3. ACTIEVE KRACHTEN: Wie is er NU ingeklokt?
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

if __name__ == '__main__':
    # Voor Render straks op host '0.0.0.0'
    app.run(debug=True, port=5000)