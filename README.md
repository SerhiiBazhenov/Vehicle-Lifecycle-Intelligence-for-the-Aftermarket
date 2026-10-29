# Vehicle Lifecycle Intelligence for the Aftermarket

## Overview

This project is designed to extract, transform, and load vehicle lifecycle data from a Power BI semantic model into a PostgreSQL staging layer. The ETL process is structured to support downstream analytics and graph-based analysis (for example, Neo4j-based lifecycle exploration).

The solution follows clean architecture principles: the entry point is minimal, business logic is separated from infrastructure, and each layer has a specific responsibility.

## Project goals

- Read data from Power BI tables and models using ADOMD.
- Discover the active Power BI Desktop port automatically when needed.
- Transfer data into PostgreSQL staging tables.
- Keep configuration flexible through environment variables.
- Make the ETL pipeline easier to maintain, test, and extend.

## Technical stack

- Python 3.x
- pandas
- Power BI ADOMD / pyadomd
- PostgreSQL
- Docker Compose
- Clean Architecture structure

## Repository structure

```text
.
├── app/
│   └── use_cases/
│       └── run_etl.py
├── domain/
│   └── ports/
│       ├── power_bi_reader.py
│       └── staging_repository.py
├── infrastructure/
│   ├── config/
│   │   └── settings.py
│   ├── powerbi/
│   │   ├── adomd_client.py
│   │   └── power_bi_port_finder.py
│   └── postgres/
│       └── staging_repository.py
├── tests/
│   └── test_etl.py
├── docker-compose.yml
├── init.sql
├── main.py
├── .env.example
├── README.md
```

## How the ETL works

1. The application reads settings from environment variables or a `.env` file.
2. The ETL bootstrap starts in `main.py`.
3. The Power BI port is detected automatically if `POWERBI_PORT` is not provided.
4. Data is read from configured Power BI tables by the ADOMD client.
5. Data is saved into the PostgreSQL staging schema (`stg`).
6. Schema creation and table writing are handled by the infrastructure repository layer.
7. The `2018-2026` table is fetched in batches and incrementally upserted by its unique `Index` column.

## Configuration

The project supports environment-based configuration. Create a `.env` file at the project root with values such as:

```env
POWERBI_DATABASE_NAME=Auto_registration_Ukraine
POWERBI_PORT=12345

POSTGRES_USER=admin
POSTGRES_PASSWORD=password123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auto_reg_db
POSTGRES_SCHEMA=stg
```

### Settings loaded by the project

- `POWERBI_DATABASE_NAME`
- `POWERBI_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_SCHEMA`

## Running the project

### 1) Create the virtual environment

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install pandas pyadomd sqlalchemy psycopg2-binary python-dotenv wmi
```

### 3) Start PostgreSQL with Docker Compose

```bash
docker compose up -d
```

This starts:

- PostgreSQL on port `5432`
- pgAdmin on port `8080`

### 4) Run the ETL

```bash
python main.py
```

The script loads Power BI data and writes it into PostgreSQL.

To test the Power BI and PostgreSQL connection with up to 1000 rows:

```bash
python main.py --table Auto_registration_monthly --limit 1000
```

The limited run writes to `stg.auto_registration_monthly_test` so it does not replace the regular staging table.

To verify the connection and write at most 100 rows from `Auto_registration_monthly`:

```bash
python main.py --limit 100
```

Or choose one table explicitly:

```bash
python main.py --table Auto_registration_monthly --limit 100
```

When `--limit` is used without `--table`, only `Auto_registration_monthly` is loaded. The staging repository replaces the destination table on each run, so this test run will replace `stg.auto_registration_monthly` with the limited result.

## Database initialization

The `init.sql` file creates the base schemas and core/mart tables used by the landing and analytical model.

## Development and testing

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

## Notes

- Power BI Desktop must be running and accessible for the ADOMD connection to work.
- The port detection logic is intended to support local Power BI Desktop environments.
- This project is a good foundation for further extension with data quality checks, validation rules, transformation steps, and additional analytical layers.

## License

This project is currently intended for internal or project-specific use.

                                         -------------------

# Vehicle Lifecycle Intelligence for the Aftermarket

## Огляд

Цей проєкт призначений для вилучення, трансформації та завантаження даних про життєвий цикл транспортних засобів із семантичної моделі Power BI у рівень PostgreSQL staging. ETL-процес побудований так, щоб підтримувати подальшу аналітику та графовий аналіз (наприклад, для дослідження життєвого циклу транспортного засобу в Neo4j).

Рішення побудоване за принципами clean architecture: точка входу мінімальна, бізнес-логіка відокремлена від інфраструктури, а кожен шар відповідає за конкретну відповідальність.

## Цілі проєкту

- Читати дані з таблиць і моделей Power BI через ADOMD.
- Автоматично знаходити активний порт Power BI Desktop, якщо це необхідно.
- Передавати дані в PostgreSQL staging-таблиці.
- Зробити конфігурацію гнучкою через змінні середовища.
- Спростити підтримку, тестування та розширення ETL-процесу.

## Технологічний стек

- Python 3.x
- pandas
- Power BI ADOMD / pyadomd
- PostgreSQL
- Docker Compose
- Архітектура в стилі Clean Architecture

## Структура репозиторію

```text
.
├── app/
│   └── use_cases/
│       └── run_etl.py
├── domain/
│   └── ports/
│       ├── power_bi_reader.py
│       └── staging_repository.py
├── infrastructure/
│   ├── config/
│   │   └── settings.py
│   ├── powerbi/
│   │   ├── adomd_client.py
│   │   └── power_bi_port_finder.py
│   └── postgres/
│       └── staging_repository.py
├── tests/
│   └── test_etl.py
├── docker-compose.yml
├── init.sql
├── main.py
├── .env.example
├── README.md
```

## Як працює ETL

1. Додаток читає налаштування з змінних середовища або файлу `.env`.
2. Точка входу запускається через `main.py`.
3. Якщо `POWERBI_PORT` не заданий, порт Power BI знаходиться автоматично.
4. Дані зчитуються з вибраних таблиць Power BI через ADOMD-клієнт.
5. Дані зберігаються у схемі PostgreSQL (`stg`).
6. Створення схеми та запис таблиць виконуються через інфраструктурний репозиторій.

## Конфігурація

Проєкт підтримує налаштування через змінні середовища. Створіть файл `.env` у корені проєкту з таким вмістом:

```env
POWERBI_DATABASE_NAME=Auto_registration_Ukraine
POWERBI_PORT=12345

POSTGRES_USER=admin
POSTGRES_PASSWORD=password123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auto_reg_db
POSTGRES_SCHEMA=stg
```

### Налаштування, які читає проєкт

- `POWERBI_DATABASE_NAME`
- `POWERBI_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_SCHEMA`

## Запуск проєкту

### 1) Створити віртуальне середовище

```bash
python -m venv .venv
```

Для Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 2) Встановити залежності

```bash
pip install pandas pyadomd sqlalchemy psycopg2-binary python-dotenv wmi
```

### 3) Запустити PostgreSQL через Docker Compose

```bash
docker compose up -d
```

Запускаються:

- PostgreSQL на порту `5432`
- pgAdmin на порту `8080`

### 4) Запустити ETL

```bash
python main.py
```

Скрипт завантажує дані з Power BI та записує їх у PostgreSQL.

Таблиця `2018-2026` зчитується частинами по 10 000 рядків. Нові рядки додаються, а рядки з наявним `Index` оновлюються в `stg.2018_2026`. Інші таблиці продовжують завантажуватися звичайним способом.

## Ініціалізація бази даних

Файл `init.sql` створює базові схеми та таблиці для core та mart шарів для аналітичної моделі.

## Розробка та тести

Запуск тестів:

```bash
python -m unittest discover -s tests -v
```

## Примітки

- Для коректної роботи з ADOMD потрібно, щоб Power BI Desktop був запущений і був доступний.
- Логіка визначення порту призначена для локального середовища Power BI Desktop.
- Проєкт є хорошою основою для подальшого розширення: перевірок якості даних, правил валідації, етапів трансформації та додаткових аналітичних шарів.

## Ліцензія

Цей проєкт наразі призначений для внутрішнього або проектного використання. 
