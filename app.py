import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# Configuração do banco de dados
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Estamos no Railway, usar PostgreSQL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print(f"Configurando PostgreSQL: {DATABASE_URL}")
else:
    # Desenvolvimento local, usar SQLite
    DATABASE_URL = 'sqlite:///instance/parking.db'
    print("Configurando SQLite")

# Configuração do Flask
app.config.update(
    SQLALCHEMY_DATABASE_URI=DATABASE_URL,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex())
)

# Inicializa o SQLAlchemy
db = SQLAlchemy(app)

# Configuração do fuso horário de Brasília
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# Models
class Vehicle(db.Model):
    __tablename__ = 'vehicle'
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50))
    vehicle_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    record_type = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Cria as tabelas se não existirem
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
    data = request.get_json()
    plate = data.get('plate', '').strip().upper()
    name = data.get('name', '').strip().upper()
    sector = data.get('sector', '').strip().upper()
    vehicle_type = data.get('vehicle_type', '').strip().upper()

    vehicle = Vehicle(
        name=name,
        plate=plate,
        sector=sector,
        vehicle_type=vehicle_type
    )
    db.session.add(vehicle)
    db.session.commit()
    return jsonify(vehicle.to_dict())

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
    data = request.get_json()
    plate = data.get('plate', '').strip().upper()  # Converte para maiúsculas
    record_type = data.get('record_type', '').strip()
    vehicle = Vehicle.query.filter_by(plate=plate).first()
    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404
    
    # Usar horário de Brasília ao criar novo registro
    now = datetime.now(TIMEZONE).replace(tzinfo=None)
    record = Record(
        vehicle_id=vehicle.id,
        record_type=record_type,
        timestamp=now
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'message': 'Record added successfully'})

@app.route('/api/vehicles/search')
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

if __name__ == '__main__':
    # Em desenvolvimento, use debug=True
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True)
    else:
        # Em produção, use as configurações padrão
        app.run()
