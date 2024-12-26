import sqlite3
import psycopg2
from datetime import datetime
import json
import os
import unicodedata

def clean_string(text):
    """Limpa e normaliza strings com caracteres especiais"""
    if not text:
        return ""
    # Remove caracteres não-ASCII
    text = text.encode('ascii', 'ignore').decode('ascii')
    # Remove espaços extras
    text = ' '.join(text.split())
    return text

def get_sqlite_data():
    """Extrai dados do SQLite"""
    conn = sqlite3.connect('instance/parking.db')
    conn.text_factory = bytes
    cursor = conn.cursor()
    
    data = {
        'vehicles': [],
        'records': []
    }
    
    try:
        cursor.execute('SELECT * FROM vehicle')
        vehicles = cursor.fetchall()
        for vehicle in vehicles:
            try:
                # Decodifica e limpa cada string
                name = clean_string(vehicle[2].decode('latin-1', errors='ignore'))
                sector = clean_string(vehicle[3].decode('latin-1', errors='ignore'))
                plate = vehicle[1].decode('latin-1', errors='ignore')
                vehicle_type = vehicle[4].decode('latin-1', errors='ignore')
                
                data['vehicles'].append({
                    'id': vehicle[0],
                    'plate': plate,
                    'name': name,
                    'sector': sector,
                    'vehicle_type': vehicle_type
                })
            except Exception as e:
                print(f"Erro ao processar veículo: {e}")
                continue
        
        cursor.execute('SELECT * FROM record')
        records = cursor.fetchall()
        for record in records:
            try:
                data['records'].append({
                    'id': record[0],
                    'plate': record[1].decode('latin-1', errors='ignore'),
                    'record_type': record[2].decode('latin-1', errors='ignore'),
                    'timestamp': record[3]
                })
            except Exception as e:
                print(f"Erro ao processar registro: {e}")
                continue
        
    except Exception as e:
        print(f"Erro ao consultar banco de dados: {e}")
        raise
    finally:
        conn.close()
    
    return data

def save_backup(data):
    """Salva backup em JSON"""
    backup_file = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(backup_file, 'w', encoding='ascii') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=True)
    return backup_file

def migrate_to_postgres(data, database_url):
    """Migra dados para PostgreSQL"""
    try:
        # Ajusta a URL se necessário
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Cria tabelas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle (
                id SERIAL PRIMARY KEY,
                plate VARCHAR(10) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                sector VARCHAR(50) NOT NULL,
                vehicle_type VARCHAR(20) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS record (
                id SERIAL PRIMARY KEY,
                plate VARCHAR(10) NOT NULL,
                record_type VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (plate) REFERENCES vehicle(plate)
            )
        """)
        
        # Limpa as tabelas existentes
        cursor.execute("DELETE FROM record")
        cursor.execute("DELETE FROM vehicle")
        
        # Insere veículos
        success_count = 0
        for vehicle in data['vehicles']:
            try:
                cursor.execute("""
                    INSERT INTO vehicle (plate, name, sector, vehicle_type)
                    VALUES (%s, %s, %s, %s)
                """, (
                    vehicle['plate'].strip(),
                    vehicle['name'].strip(),
                    vehicle['sector'].strip(),
                    vehicle['vehicle_type'].strip()
                ))
                success_count += 1
                if success_count % 10 == 0:  # Mostra progresso a cada 10 registros
                    print(f"Progresso: {success_count}/{len(data['vehicles'])} veículos migrados")
            except Exception as e:
                print(f"Erro ao inserir veículo {vehicle['plate']}: {e}")
        
        # Insere registros
        for record in data['records']:
            try:
                cursor.execute("""
                    INSERT INTO record (plate, record_type, timestamp)
                    VALUES (%s, %s, %s)
                """, (record['plate'], record['record_type'], record['timestamp']))
            except Exception as e:
                print(f"Erro ao inserir registro {record['plate']}: {e}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro na migração: {e}")
        return False

if __name__ == "__main__":
    print("Script de Migração SQLite -> PostgreSQL")
    print("-" * 50)
    
    # Solicita a URL do PostgreSQL
    print("\nCole a URL do PostgreSQL do Railway:")
    database_url = input().strip()
    
    if not database_url:
        print("Erro: URL do banco de dados não fornecida!")
        exit(1)
    
    # Extrai dados do SQLite
    print("\nExtraindo dados do SQLite...")
    try:
        data = get_sqlite_data()
        print(f"Dados extraídos: {len(data['vehicles'])} veículos e {len(data['records'])} registros")
    except Exception as e:
        print(f"Erro ao extrair dados do SQLite: {e}")
        exit(1)
    
    # Salva backup
    print("\nSalvando backup...")
    try:
        backup_file = save_backup(data)
        print(f"Backup salvo em: {backup_file}")
    except Exception as e:
        print(f"Erro ao salvar backup: {e}")
        exit(1)
    
    # Migra dados
    print("\nMigrando dados para PostgreSQL...")
    if migrate_to_postgres(data, database_url):
        print("\nMigração concluída com sucesso! 🎉")
        print(f"Veículos migrados: {len(data['vehicles'])}")
        print(f"Registros migrados: {len(data['records'])}")
    else:
        print("\n❌ Erro na migração. Verifique os logs acima.")
        print("Você ainda tem o backup em:", backup_file)
