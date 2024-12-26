-- Primeiro, remove as tabelas se existirem
DROP TABLE IF EXISTS record;
DROP TABLE IF EXISTS vehicle;

-- Cria a tabela vehicle
CREATE TABLE vehicle (
    id SERIAL PRIMARY KEY,
    plate VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50),
    vehicle_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cria a tabela record
CREATE TABLE record (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER NOT NULL,
    record_type VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicle(id) ON DELETE CASCADE
);

-- Cria índices para melhor performance
CREATE INDEX idx_vehicle_plate ON vehicle(plate);
CREATE INDEX idx_record_vehicle ON record(vehicle_id);
CREATE INDEX idx_record_timestamp ON record(timestamp);