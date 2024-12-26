import os
import psycopg2
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

def init_db():
    """Inicializa o banco de dados usando SQL puro"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("Error: DATABASE_URL não configurada!")
        return
    
    # Lê o arquivo SQL
    with open('create_tables.sql', 'r') as file:
        sql = file.read()
    
    # Conecta ao PostgreSQL
    print("Conectando ao PostgreSQL...")
    pg_params = parse_postgres_url(DATABASE_URL)
    conn = psycopg2.connect(**pg_params)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        print("Executando SQL...")
        cur.execute(sql)
        print("Tabelas criadas com sucesso!")
        
        # Verifica as tabelas criadas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        print("Tabelas existentes:", [table[0] for table in tables])
        
    except Exception as e:
        print(f"Erro ao criar tabelas: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    init_db()