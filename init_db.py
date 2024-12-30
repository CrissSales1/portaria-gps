import os
import sqlite3
from app import app, db

def init_db():
    """Inicializa o banco de dados"""
    try:
        # Cria o diretório instance se não existir
        os.makedirs('instance', exist_ok=True)
        
        with app.app_context():
            # Cria todas as tabelas usando SQLAlchemy
            db.create_all()
            print("Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")
        raise

if __name__ == '__main__':
    init_db()