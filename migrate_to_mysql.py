import sqlite3
import mysql.connector
from datetime import datetime
import json

def get_sqlite_data():
    """Extrai dados do SQLite"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Obtém dados das tabelas
    data = {
        'vehicles': [],
        'records': []
    }
    
    # Extrai veículos
    cursor.execute('SELECT * FROM vehicle')
    vehicles = cursor.fetchall()
    for vehicle in vehicles:
        data['vehicles'].append({
            'id': vehicle[0],
            'plate': vehicle[1],
            'name': vehicle[2],
            'sector': vehicle[3],
            'vehicle_type': vehicle[4]
        })
    
    # Extrai registros
    cursor.execute('SELECT * FROM record')
    records = cursor.fetchall()
    for record in records:
        data['records'].append({
            'id': record[0],
            'plate': record[1],
            'record_type': record[2],
            'timestamp': record[3]
        })
    
    conn.close()
    return data

def save_backup(data):
    """Salva backup em JSON"""
    backup_file = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    return backup_file

def migrate_to_mysql(data, host, user, password, database):
    """Migra dados para MySQL"""
    try:
        # Conecta ao MySQL
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        
        # Cria tabelas se não existirem
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(10) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                sector VARCHAR(50) NOT NULL,
                vehicle_type VARCHAR(20) NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS record (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(10) NOT NULL,
                record_type VARCHAR(10) NOT NULL,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (plate) REFERENCES vehicle(plate)
            )
        """)
        
        # Insere veículos
        for vehicle in data['vehicles']:
            cursor.execute("""
                INSERT INTO vehicle (plate, name, sector, vehicle_type)
                VALUES (%s, %s, %s, %s)
            """, (vehicle['plate'], vehicle['name'], vehicle['sector'], vehicle['vehicle_type']))
        
        # Insere registros
        for record in data['records']:
            cursor.execute("""
                INSERT INTO record (plate, record_type, timestamp)
                VALUES (%s, %s, %s)
            """, (record['plate'], record['record_type'], record['timestamp']))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro na migração: {e}")
        return False

if __name__ == "__main__":
    # Extrai dados do SQLite
    print("Extraindo dados do SQLite...")
    data = get_sqlite_data()
    
    # Salva backup
    print("Salvando backup...")
    backup_file = save_backup(data)
    print(f"Backup salvo em: {backup_file}")
    
    # Solicita dados do MySQL
    print("\nInsira os dados do MySQL do cPanel:")
    host = input("Host: ")
    user = input("Usuário: ")
    password = input("Senha: ")
    database = input("Nome do Banco: ")
    
    # Migra dados
    print("\nMigrando dados para MySQL...")
    if migrate_to_mysql(data, host, user, password, database):
        print("Migração concluída com sucesso!")
    else:
        print("Erro na migração. Verifique os logs acima.")
