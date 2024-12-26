import os
import sqlite3
import psycopg2
from datetime import datetime
from urllib.parse import urlparse

def parse_postgres_url(url):
    """Converte a URL do PostgreSQL em parâmetros de conexão"""
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    
    result = urlparse(url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    
    return {
        'dbname': database,
        'user': username,
        'password': password,
        'host': hostname,
        'port': port
    }

def migrate_data():
    """Migra dados do SQLite para o PostgreSQL"""
    # Conecta ao SQLite
    sqlite_conn = sqlite3.connect('instance/parking.db')
    sqlite_cur = sqlite_conn.cursor()

    # Conecta ao PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("Error: DATABASE_URL não configurada!")
        return

    pg_params = parse_postgres_url(DATABASE_URL)
    pg_conn = psycopg2.connect(**pg_params)
    pg_cur = pg_conn.cursor()

    try:
        # Migra veículos
        sqlite_cur.execute('SELECT plate, name, sector, vehicle_type, created_at FROM vehicle')
        vehicles = sqlite_cur.fetchall()
        
        id_map = {}  # Mapeia IDs antigos para novos
        
        for vehicle in vehicles:
            plate, name, sector, vehicle_type, created_at = vehicle
            pg_cur.execute('''
                INSERT INTO vehicle (plate, name, sector, vehicle_type, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (plate, name, sector, vehicle_type, created_at))
            
            new_id = pg_cur.fetchone()[0]
            old_id = sqlite_cur.execute('SELECT id FROM vehicle WHERE plate = ?', (plate,)).fetchone()[0]
            id_map[old_id] = new_id

        # Migra registros
        sqlite_cur.execute('SELECT vehicle_id, record_type, timestamp FROM record')
        records = sqlite_cur.fetchall()
        
        for record in records:
            old_vehicle_id, record_type, timestamp = record
            new_vehicle_id = id_map.get(old_vehicle_id)
            if new_vehicle_id:
                pg_cur.execute('''
                    INSERT INTO record (vehicle_id, record_type, timestamp)
                    VALUES (%s, %s, %s)
                ''', (new_vehicle_id, record_type, timestamp))

        pg_conn.commit()
        print("Migração concluída com sucesso!")

    except Exception as e:
        pg_conn.rollback()
        print(f"Erro durante a migração: {str(e)}")
        raise
    finally:
        sqlite_cur.close()
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()

if __name__ == '__main__':
    migrate_data()