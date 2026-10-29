-- ==========================================================
-- 1. СТВОРЕННЯ СХЕМ
-- ==========================================================
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

-- ==========================================================
-- 2. CORE SCHEMA (Ваша модель з DrawSQL, адаптована)
-- ==========================================================

CREATE TABLE core.dim_date(
    "date_value" DATE NOT NULL,
    "calendar_year" SMALLINT NOT NULL,
    "quarter_number" SMALLINT NOT NULL,
    "month_number" SMALLINT NOT NULL,
    "day_of_month" SMALLINT NOT NULL,
    "month_start" DATE NOT NULL,
    "is_weekend" BOOLEAN NOT NULL,
    PRIMARY KEY("date_value")
);

CREATE TABLE core.dim_operation(
    "operation_id" bigserial NOT NULL,
    "oper_code" INTEGER NULL,
    "oper_name" TEXT NULL,
    PRIMARY KEY("operation_id"),
    CONSTRAINT "dim_operation_oper_code_oper_name_unique" UNIQUE("oper_code", "oper_name")
);

CREATE TABLE core.dim_vehicle(
    "vehicle_id" bigserial NOT NULL,
    "brand" TEXT NULL,
    "model" TEXT NULL,
    "make_year" SMALLINT NULL,
    "kind" TEXT NULL,
    "body" TEXT NULL,
    "fuel" TEXT NULL,
    "power_kw" DECIMAL(12, 3) NULL,
    "BaseModel" TEXT NOT NULL,
    "Brand&Model" TEXT NOT NULL,
    "Brand&Model&MakeYear" TEXT NOT NULL,
    "Brand&Model&MakeYear(in period_5 year)" TEXT NOT NULL,
    PRIMARY KEY("vehicle_id")
);

CREATE TABLE core.dim_registration_context(
    "registration_context_id" bigserial NOT NULL,
    "person" TEXT NULL,
    "reg_addr_koatuu" BIGINT NULL,
    "dep_code" INTEGER NULL,
    "dep" TEXT NULL,
    "color" TEXT NULL,
    "purpose" TEXT NULL,
    PRIMARY KEY("registration_context_id")
);

CREATE TABLE core.dim_vin_origin(
    "vin_origin_id" bigserial NOT NULL,
    "WMI_Prefix" TEXT NOT NULL,
    "char_1" TEXT NULL,
    "char_2" TEXT NULL,
    "region" TEXT NULL,
    "country" TEXT NULL,
    PRIMARY KEY("vin_origin_id"),
    CONSTRAINT "dim_vin_origin_wmi_prefix_unique" UNIQUE("WMI_Prefix")
);

CREATE TABLE core.fact_registration(
    "registration_id" bigserial NOT NULL,
    "registration_date" DATE NOT NULL,
    "operation_id" BIGINT NULL,
    "vehicle_id" BIGINT NULL,
    "registration_context_id" BIGINT NULL,
    "vin_origin_id" BIGINT NULL,
    "vin" TEXT NULL,
    "registration_number" TEXT NULL,
    "capacity" BIGINT NULL,
    "own_weight" BIGINT NULL,
    "total_weight" BIGINT NULL,
    PRIMARY KEY("registration_id"),
    CONSTRAINT "fact_registration_registration_date_foreign" FOREIGN KEY("registration_date") REFERENCES core.dim_date("date_value"),
    CONSTRAINT "fact_registration_registration_context_id_foreign" FOREIGN KEY("registration_context_id") REFERENCES core.dim_registration_context("registration_context_id"),
    CONSTRAINT "fact_registration_vehicle_id_foreign" FOREIGN KEY("vehicle_id") REFERENCES core.dim_vehicle("vehicle_id"),
    CONSTRAINT "fact_registration_operation_id_foreign" FOREIGN KEY("operation_id") REFERENCES core.dim_operation("operation_id"),
    CONSTRAINT "fact_registration_vin_origin_id_foreign" FOREIGN KEY("vin_origin_id") REFERENCES core.dim_vin_origin("vin_origin_id")
);

-- Оптимізація індексами (додано для швидкодії)
CREATE INDEX idx_fact_reg_vin ON core.fact_registration("vin");
CREATE INDEX idx_fact_reg_date ON core.fact_registration("registration_date");

-- ==========================================================
-- 3. MART SCHEMA (Для Neo4j та Report Ready Data)
-- ==========================================================

-- View для швидкого отримання списку подій для графу (Neo4j)
CREATE VIEW mart.vehicle_lifecycle_events AS
SELECT 
    f.registration_id,
    f.vin,
    f.registration_date,
    v.brand,
    v.model,
    o.oper_name as event_type,
    c.person as owner_name
FROM core.fact_registration f
JOIN core.dim_vehicle v ON f.vehicle_id = v.vehicle_id
JOIN core.dim_operation o ON f.operation_id = o.operation_id
LEFT JOIN core.dim_registration_context c ON f.registration_context_id = c.registration_context_id;