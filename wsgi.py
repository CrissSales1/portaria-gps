from app import app, db
import sys

print("Iniciando aplicação...")
print("Python version:", sys.version)
print("SQLAlchemy Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

# Cria as tabelas do banco de dados
with app.app_context():
    print("Criando tabelas no banco de dados...")
    try:
        db.create_all()
        print("Tabelas criadas com sucesso!")
        # Lista as tabelas criadas
        tables = db.engine.table_names()
        print("Tabelas existentes:", tables)
    except Exception as e:
        print("Erro ao criar tabelas:", str(e))
        raise

if __name__ == "__main__":
    app.run()
