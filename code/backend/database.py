# database.py
import sqlite3

def create_database():
    try:
        conn = sqlite3.connect('maritime.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                speed REAL,
                type TEXT,
                timestamp TEXT,                
                significance TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating database: {e}")
    finally:
        if conn: 
            conn.close()

def store_in_database(data):
    
    if data.get('latitude') is None or data.get('longitude') is None:
        print("Skipping contact with missing coordinates")
        return
        
    try:
        conn = sqlite3.connect('maritime.db')
        c = conn.cursor()
        if all(key in data for key in ['latitude', 'longitude', 'speed', 'type', 'timestamp', 'significance']):
            c.execute('''
                INSERT INTO reports (latitude, longitude, speed, type, timestamp, significance) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['latitude'], data['longitude'], data['speed'], data['type'], data['timestamp'], data['significance']))
            conn.commit()
        else:
            print("Error: Missing required data fields.")
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
    finally:
        if conn:
            conn.close()

def get_latest_contact():
    try:
        conn = sqlite3.connect('maritime.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT latitude, longitude, speed, type, significance, timestamp 
            FROM reports 
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL 
            ORDER BY id DESC LIMIT 1
        ''')
        result = c.fetchone()
        if result:
            return {
                'latitude': result[0],
                'longitude': result[1],
                'speed': result[2],
                'type': result[3],
                'significance': result[4],
                'timestamp': result[5]
            }
        else:
            return None
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_contacts():
    try:
        conn = sqlite3.connect('maritime.db')
        cursor = conn.cursor()
       
        cursor.execute('''
            SELECT * FROM reports 
            WHERE latitude IS NOT NULL 
            AND longitude IS NOT NULL
        ''')
        contacts = cursor.fetchall()

        contact_list = []
        for contact in contacts:
            contact_list.append({
                'latitude': contact[1],
                'longitude': contact[2],
                'speed': contact[3],
                'type': contact[4],
                'significance': contact[6],
                'timestamp': contact[5]
            })
        return contact_list
    except Exception as e:
        print(f"Error fetching all contacts: {e}")
        return []
    finally:
        if conn:
            conn.close()