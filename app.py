import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz
import pandas as pd

app = Flask(__name__)

# Configuração do fuso horário
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# Configuração do banco de dados
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Estamos no Railway, usar PostgreSQL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print(f"Configurando PostgreSQL: {DATABASE_URL}")
else:
    # Desenvolvimento local, usar SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    DATABASE_URL = f'sqlite:///{os.path.join(basedir, "instance", "parking.db")}'
    print("Configurando SQLite:", DATABASE_URL)

# Configuração do Flask
app.config.update(
    SQLALCHEMY_DATABASE_URI=DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex())
)

# Inicializa o SQLAlchemy
db = SQLAlchemy(app)

def get_current_time():
    """Retorna o horário atual no fuso horário correto"""
    return datetime.now(TIMEZONE).replace(tzinfo=None)

# Models
class Vehicle(db.Model):
    __tablename__ = 'vehicle'
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50))
    vehicle_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=get_current_time)
    records = db.relationship('Record', backref='vehicle', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'plate': self.plate,
            'name': self.name,
            'sector': self.sector,
            'vehicle_type': self.vehicle_type,
            'created_at': self.created_at
        }

class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id', ondelete='CASCADE'), nullable=False)
    record_type = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=get_current_time)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vehicles')
def vehicles():
    return render_template('vehicles.html')

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    vehicles = Vehicle.query.all()
    return jsonify([v.to_dict() for v in vehicles])

@app.route('/api/vehicles', methods=['POST'])
def add_vehicle():
    try:
        data = request.json
        plate = data.get('plate', '').strip().upper()
        name = data.get('name', '').strip().upper()
        sector = data.get('sector', '').strip().upper()
        vehicle_type = data.get('vehicle_type', '').strip().upper()

        # Validações
        if not plate or not name:
            return jsonify({'error': 'Placa e nome são obrigatórios'}), 400

        # Verifica se já existe um veículo com essa placa
        existing_vehicle = Vehicle.query.filter_by(plate=plate).first()
        if existing_vehicle:
            return jsonify({'error': 'Já existe um veículo com essa placa'}), 400

        # Cria o novo veículo
        vehicle = Vehicle(
            plate=plate,
            name=name,
            sector=sector,
            vehicle_type=vehicle_type
        )

        db.session.add(vehicle)
        db.session.commit()

        return jsonify(vehicle.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao adicionar veículo: {str(e)}")
        return jsonify({'error': 'Erro ao adicionar veículo'}), 500

@app.route('/api/vehicles/<int:id>', methods=['PUT'])
def update_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    data = request.get_json()
    
    vehicle.name = data.get('name', '').strip().upper()
    vehicle.plate = data.get('plate', '').strip().upper()
    vehicle.sector = data.get('sector', '').strip().upper()
    vehicle.vehicle_type = data.get('vehicle_type', '').strip().upper()
    
    db.session.commit()
    return jsonify(vehicle.to_dict())

@app.route('/api/vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
            
        db.session.delete(vehicle)
        db.session.commit()
        return jsonify({'message': 'Vehicle deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/records', methods=['POST'])
def add_record():
    try:
        data = request.json
        vehicle_id = data.get('vehicle_id')
        record_type = data.get('record_type', '').strip()

        # Validação e normalização do tipo de registro
        if record_type.upper() not in ['ENTRADA', 'SAÍDA']:
            return jsonify({'error': 'Tipo de registro inválido'}), 400

        # Garante que o tipo está correto
        record_type = 'ENTRADA' if record_type.upper() == 'ENTRADA' else 'SAÍDA'

        if not vehicle_id or not record_type:
            return jsonify({'error': 'ID do veículo e tipo são obrigatórios'}), 400

        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'error': 'Veículo não encontrado'}), 404

        record = Record(
            vehicle_id=vehicle_id,
            record_type=record_type,
            timestamp=get_current_time()  # Usa o horário local
        )
        db.session.add(record)
        db.session.commit()

        return jsonify({'message': 'Registro adicionado com sucesso'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao adicionar registro: {str(e)}")
        return jsonify({'error': 'Erro ao adicionar registro'}), 500

@app.route('/api/records', methods=['GET'])
def get_records():
    try:
        # Parâmetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        record_type = request.args.get('type')
        plate = request.args.get('plate', '').strip().upper()

        # Query base
        query = db.session.query(Record, Vehicle).join(Vehicle)
        
        # Aplica filtros
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            query = query.filter(Record.timestamp >= start)

        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Record.timestamp <= end)

        if record_type and record_type.upper() in ['ENTRADA', 'SAIDA']:
            query = query.filter(Record.record_type == record_type.upper())

        if plate:
            query = query.filter(Vehicle.plate == plate)

        # Ordena por timestamp decrescente
        records = query.order_by(Record.timestamp.desc()).all()

        # Formata a resposta
        result = []
        for record, vehicle in records:
            result.append({
                'id': record.id,
                'timestamp': record.timestamp,
                'record_type': record.record_type,
                'vehicle': {
                    'id': vehicle.id,
                    'plate': vehicle.plate,
                    'name': vehicle.name,
                    'sector': vehicle.sector,
                    'vehicle_type': vehicle.vehicle_type
                }
            })

        return jsonify(result)

    except Exception as e:
        print(f"Erro ao buscar registros: {str(e)}")
        return jsonify({'error': 'Erro ao buscar registros'}), 500

@app.route('/api/recent-records')
def get_recent_records():
    records = db.session.query(Record, Vehicle).join(Vehicle).order_by(Record.timestamp.desc()).limit(10).all()
    return jsonify([{
        'id': record.Record.id,
        'timestamp': TIMEZONE.localize(record.Record.timestamp).strftime('%d/%m/%Y %H:%M:%S'),
        'record_type': record.Record.record_type,
        'plate': record.Vehicle.plate,
        'name': record.Vehicle.name,
        'sector': record.Vehicle.sector
    } for record in records])

@app.route('/api/clear-records', methods=['POST'])
def clear_records():
    try:
        db.session.query(Record).delete()
        db.session.commit()
        return jsonify({'message': 'Registros limpos com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_database', methods=['POST'])
def clear_database():
    try:
        # Exclui todos os registros
        Record.query.delete()
        
        # Exclui todos os veículos
        Vehicle.query.delete()
        
        # Commit das alterações
        db.session.commit()
        
        return jsonify({
            'message': 'Banco de dados limpo com sucesso'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar banco de dados: {str(e)}")
        return jsonify({
            'error': 'Erro ao limpar banco de dados'
        }), 500

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/api/reports')
def get_reports():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    record_type = request.args.get('record_type')  # 'entrada', 'saída' ou todos
    
    query = db.session.query(Record, Vehicle).join(Vehicle)
    
    if start_date:
        start = TIMEZONE.localize(datetime.strptime(start_date, '%Y-%m-%d'))
        query = query.filter(Record.timestamp >= start)
    if end_date:
        end = TIMEZONE.localize(datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        query = query.filter(Record.timestamp < end)
    if record_type and record_type != 'todos':
        query = query.filter(Record.record_type == record_type)
    
    records = query.order_by(Record.timestamp.desc()).all()
    
    return jsonify([{
        'id': record.Record.id,
        'timestamp': TIMEZONE.localize(record.Record.timestamp).strftime('%d/%m/%Y %H:%M:%S'),
        'record_type': record.Record.record_type,
        'plate': record.Vehicle.plate,
        'name': record.Vehicle.name,
        'sector': record.Vehicle.sector
    } for record in records])

@app.route('/api/search-vehicles')
def search_vehicles():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify([])

    vehicles = Vehicle.query.filter(
        db.or_(
            Vehicle.plate.ilike(f'%{query}%'),
            Vehicle.name.ilike(f'%{query}%'),
            Vehicle.sector.ilike(f'%{query}%')
        )
    ).all()

    return jsonify([{
        'id': v.id,
        'name': v.name,
        'plate': v.plate,
        'sector': v.sector,
        'vehicle_type': v.vehicle_type
    } for v in vehicles])

@app.route('/api/import_vehicles', methods=['POST'])
def import_vehicles():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.xlsx'):
            return jsonify({'error': 'Formato de arquivo inválido. Use .xlsx'}), 400

        # Lê o arquivo Excel
        df = pd.read_excel(file)
        
        # Verifica as colunas necessárias
        required_columns = ['Placa', 'Nome', 'Setor', 'Tipo']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Arquivo Excel inválido. Verifique as colunas necessárias.'}), 400

        # Inicializa contadores
        imported = 0
        duplicates = 0
        errors = 0

        # Processa cada linha
        for _, row in df.iterrows():
            try:
                plate = str(row['Placa']).strip().upper()
                name = str(row['Nome']).strip().upper()
                sector = str(row['Setor']).strip().upper()
                vehicle_type = str(row['Tipo']).strip().lower()

                # Validações
                if not plate or not name:
                    errors += 1
                    continue

                # Normaliza o tipo de veículo
                if vehicle_type not in ['carro', 'moto']:
                    vehicle_type = 'carro'  # valor padrão

                # Verifica se já existe um veículo com essa placa
                existing_vehicle = Vehicle.query.filter_by(plate=plate).first()
                if existing_vehicle:
                    duplicates += 1
                    continue

                # Cria o novo veículo
                vehicle = Vehicle(
                    plate=plate,
                    name=name,
                    sector=sector,
                    vehicle_type=vehicle_type
                )
                db.session.add(vehicle)
                imported += 1

            except Exception as e:
                print(f"Erro ao processar linha: {str(e)}")
                errors += 1
                continue

        # Commit das alterações
        db.session.commit()

        return jsonify({
            'message': 'Importação concluída com sucesso',
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erro na importação: {str(e)}")
        return jsonify({'error': 'Erro ao processar arquivo'}), 500

if __name__ == '__main__':
    # Em desenvolvimento, use debug=True
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True)
    else:
        # Em produção, use as configurações padrão
        app.run()
