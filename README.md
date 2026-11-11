# Reservation Scheduler Service

Owns the reservations table and exposes /api/v1/reservations. It calls Registry by HTTP; it never connects to the Registry database. Its separate repository should contain this folder's files only.

Set DATABASE_URL and REGISTRY_BASE_URL in PowerShell:

    $env:DATABASE_URL = "postgresql+psycopg://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5434/scheduler"
    $env:REGISTRY_BASE_URL = "http://localhost:8001"
    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002

Start a PostgreSQL database initialized with db/schema.sql and start Registry first. The root compose.yaml does this automatically. Run unit tests from this folder:

    .\.venv\Scripts\python.exe -m pytest tests -q

The GiST exclusion constraint in db/schema.sql prevents concurrent overlapping confirmed bookings. A pre-insert availability query only gives a friendly early error. Schema.sql initializes new databases; it is not an upgrade migration.

