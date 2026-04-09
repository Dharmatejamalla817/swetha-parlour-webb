from flask import Flask, render_template, request, redirect
from datetime import datetime, timedelta  
import sqlite3
import os
app = Flask(__name__)
DB_FILE = 'database.db'

# --- SAFETY CHECK: This builds the database automatically ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Create Services Table
    cursor.execute("CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY, category TEXT, name TEXT, price TEXT)")
    # Create Bookings Table
    cursor.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT, service_id INTEGER, booking_date TEXT, booking_time TEXT)")
    
    # Check if we need to add the menu items
    check = cursor.execute("SELECT count(*) FROM services").fetchone()
    if check[0] == 0:
        menu = [
             ('Facial', 'Clean up', '300'),
        ('Facial', 'Fruit Facial', '350'),
        ('Facial', 'Gold Facial', '600'),
        ('Facial', 'Diamond Facial', '700'),
        ('Facial', 'O3+ Acne Treatment', '3000'),
        ('Threading', 'Upper Lip', '10'),
        ('Threading', 'Eyebrows', '40'),
        ('Threading', 'Full Face', '150'),
        ('Waxing', 'Under Arms', '100'),
        ('Waxing', 'Full Legs', '400'),
        ('Waxing', 'Face', '250'),
        ('Manicure', 'Classic Manicure', '700'),
        ('Hair Cut', 'U Cut', '100'),
        ('Hair Cut', 'Step Cut', '300'),
        ('Hair Cut', 'Layer Cut', '500'),
        ('Hair Treatment', 'Hair Spa', '1000-2000'),
        ('Hair Color', 'Global Highlights', '1000-2000')
        ]
        cursor.executemany("INSERT INTO services (category, name, price) VALUES (?, ?, ?)", menu)
    
    conn.commit()
    conn.close()

# Run the safety check
init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    services = conn.execute('SELECT * FROM services').fetchall()
    conn.close()
    return render_template('index.html', services=services)



@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    service_id = request.form['service']
    date = request.form['date']
    time_str = request.form['time']
    
    # 1. Convert the input time string to a Python time object
    requested_time = datetime.strptime(f"{date} {time_str}", '%Y-%m-%d %H:%M')
    
    # 2. Define the buffer (2 hours before and 2 hours after)
    start_buffer = (requested_time - timedelta(hours=2)).strftime('%H:%M')
    end_buffer = (requested_time + timedelta(hours=2)).strftime('%H:%M')
    
    conn = get_db_connection()
    
    # 3. Check the database for any booking on the SAME date 
    # that falls within the 2-hour window
    existing_booking = conn.execute('''
        SELECT * FROM bookings 
        WHERE booking_date = ? 
        AND booking_time > ? 
        AND booking_time < ?
    ''', (date, start_buffer, end_buffer)).fetchone()
    
    if existing_booking:
        conn.close()
        return f"<h1>Slot Unavailable</h1><p>Sorry {name}, this time is too close to another appointment. Please pick a time at least 2 hours before or after {existing_booking['booking_time']}.</p><a href='/'>Try again</a>"

    # 4. If no conflict, proceed with the booking
    conn.execute('INSERT INTO bookings (customer_name, service_id, booking_date, booking_time) VALUES (?, ?, ?, ?)',
                 (name, service_id, date, time_str))
    conn.commit()
    conn.close()
    
    return render_template('confirm.html', name=name, date=date)


    @app.route('/admin')
def admin():
    try:
        conn = get_db_connection()
        # We use a JOIN to get the service name and the price
        bookings = conn.execute('''
            SELECT bookings.id, bookings.customer_name, bookings.booking_date, 
                   bookings.booking_time, services.name as service_name
            FROM bookings 
            JOIN services ON bookings.service_id = services.id
        ''').fetchall()
        
        readable_bookings = []
        for b in bookings:
            b_dict = dict(b)
            # Safe time formatting
            try:
                time_obj = datetime.strptime(b['booking_time'], '%H:%M')
                b_dict['display_time'] = time_obj.strftime('%I:%M %p')
            except:
                b_dict['display_time'] = b['booking_time'] # Fallback if time is messy
            
            readable_bookings.append(b_dict)
            
        conn.close()
        return render_template('admin.html', bookings=readable_bookings)
    except Exception as e:
        return f"<h1>Admin Error</h1><p>{str(e)}</p>" # This will tell us the EXACT error
    

if __name__ == '__main__':
    app.run(debug=False)
