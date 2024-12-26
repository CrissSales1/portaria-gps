import sqlite3
import psycopg2
from datetime import datetime
import os
from urllib.parse import urlparse

# Configuração dos bancos de dados
SQLITE_DB = 'instance/parking.db'
POSTGRES_URL = os.environ.get('DATABASE_URL', '')

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
    """Migra dados do SQLite para PostgreSQL"""
    # Conecta ao SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cur = sqlite_conn.cursor()
    
    # Conecta ao PostgreSQL
    pg_params = parse_postgres_url(POSTGRES_URL)
    pg_conn = psycopg2.connect(**pg_params)
    pg_cur = pg_conn.cursor()
    
    try:
        # 1. Migra veículos
        print("Migrando veículos...")
        sqlite_cur.execute('SELECT id, name, plate, sector, vehicle_type, created_at FROM vehicle')
        vehicles = sqlite_cur.fetchall()
        
        for vehicle in vehicles:
            # Converte created_at para timestamp se necessário
            created_at = vehicle[5] if vehicle[5] else datetime.utcnow()
            
            pg_cur.execute('''
                INSERT INTO vehicle (id, name, plate, sector, vehicle_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    plate = EXCLUDED.plate,
                    sector = EXCLUDED.sector,
                    vehicle_type = EXCLUDED.vehicle_type,
                    created_at = EXCLUDED.created_at
            ''', vehicle)
        
        print(f"Migrados {len(vehicles)} veículos")
        
        # 2. Migra registros
        print("Migrando registros...")
        sqlite_cur.execute('SELECT id, vehicle_id, record_type, timestamp FROM record')
        records = sqlite_cur.fetchall()
        
        for record in records:
            # Converte timestamp para timestamp se necessário
            timestamp = record[3] if record[3] else datetime.utcnow()
            
            pg_cur.execute('''
                INSERT INTO record (id, vehicle_id, record_type, timestamp)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    vehicle_id = EXCLUDED.vehicle_id,
                    record_type = EXCLUDED.record_type,
                    timestamp = EXCLUDED.timestamp
            ''', record)
        
        print(f"Migrados {len(records)} registros")
        
        # Commit das alterações
        pg_conn.commit()
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Erro durante a migração: {str(e)}")
        raise
    
    finally:
        # Fecha conexões
        sqlite_cur.close()
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()

if __name__ == '__main__':
    if not POSTGRES_URL:
        print("Error: DATABASE_URL não configurada!")
    else:
        migrate_data()