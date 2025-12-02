------------------------------------------------------------------------------------
-- POSTGRES DATABASE INITIALIZATION SCRIPT (PostgreSQL)
------------------------------------------------------------------------------------

CREATE DATABASE dlms_reader_db;
\c dlms_reader_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dlms_reader_user') THEN
      CREATE USER dlms_reader_user WITH PASSWORD '123456';
   END IF;
END$$;

GRANT ALL PRIVILEGES ON DATABASE dlms_reader_db TO dlms_reader_user;
GRANT USAGE ON SCHEMA public TO dlms_reader_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dlms_reader_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dlms_reader_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO dlms_reader_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO dlms_reader_user;

------------------------------------------------------------------------------------
-- Enum types creation
------------------------------------------------------------------------------------
CREATE TYPE medium_enum AS ENUM ('TCP', 'SERIAL');
CREATE TYPE profile_enum AS ENUM ('WRAPPER', 'HDLC_TUNNELING');
CREATE TYPE auth_enum AS ENUM ('NONE', 'LLS', 'HLS');
CREATE TYPE phase_enum AS ENUM ('A','B','C','TOTAL','NEUTRAL','NONE');
CREATE TYPE direction_enum AS ENUM ('IMPORT','EXPORT','NONE');
CREATE TYPE quantity_enum AS ENUM (
  'ENERGY_ACTIVE',
  'ENERGY_REACTIVE',
  'POWER_ACTIVE',
  'POWER_REACTIVE',
  'VOLTAGE',
  'CURRENT',
  'POWER_FACTOR'
);

------------------------------------------------------------------------------------
-- Table creation
------------------------------------------------------------------------------------
CREATE TABLE devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(255) NOT NULL,
  description text,
  serial_number varchar(255) UNIQUE,
  brand varchar(255),
  model varchar(255),
  created_at timestamp NOT NULL DEFAULT now(),
  updated_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE comm_endpoints (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  medium medium_enum NOT NULL,
  profile profile_enum NOT NULL,
  ip inet,
  port integer,
  serial_port text,
  baud_rate integer,
  is_primary boolean NOT NULL DEFAULT false,
  created_at timestamp NOT NULL DEFAULT now(),
  updated_at timestamp NOT NULL DEFAULT now(),
  CHECK ( (medium <> 'TCP') OR (ip IS NOT NULL AND port IS NOT NULL) ),
  CHECK ( (medium <> 'SERIAL') OR (serial_port IS NOT NULL AND baud_rate IS NOT NULL) )
);

CREATE TABLE device_addressing (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  client_address integer NOT NULL,
  server_address integer NOT NULL,
  use_logical_name boolean NOT NULL DEFAULT true,
  password text,
  created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE negotiated_params (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  endpoint_id uuid NOT NULL REFERENCES comm_endpoints(id) ON DELETE CASCADE,
  max_info_rx integer,
  max_info_tx integer,
  win integer,
  max_pdu integer,
  created_at timestamp NOT NULL DEFAULT now(),
  updated_at timestamp NOT NULL DEFAULT now(),
  CONSTRAINT negotiated_params_device_endpoint_uniq UNIQUE (device_id, endpoint_id)
);

CREATE TABLE measurements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  endpoint_id uuid REFERENCES comm_endpoints(id) ON DELETE SET NULL,
  obis text NOT NULL,
  quantity quantity_enum NOT NULL,
  direction direction_enum NOT NULL,
  phase phase_enum NOT NULL,
  value double precision NOT NULL,
  unit text NOT NULL,
  ts_meter timestamp,
  ts_captured timestamp NOT NULL DEFAULT now()
);

------------------------------------------------------------------------------------
-- CONSTRAINTS / Indexes creation
------------------------------------------------------------------------------------
CREATE UNIQUE INDEX comm_endpoints_tcp_uniq
  ON comm_endpoints (device_id, medium, profile, ip, port)
  WHERE medium = 'TCP';

CREATE UNIQUE INDEX comm_endpoints_serial_uniq
  ON comm_endpoints (device_id, medium, profile, serial_port, baud_rate)
  WHERE medium = 'SERIAL';

CREATE INDEX comm_endpoints_device_idx ON comm_endpoints(device_id);
CREATE INDEX measurements_dev_time_idx ON measurements (device_id, ts_meter DESC);
CREATE INDEX measurements_quantity_idx ON measurements (quantity, direction, phase);
