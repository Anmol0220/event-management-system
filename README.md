# Event Management System

A full-stack Event Management System built with FastAPI, SQLAlchemy 2.x, PostgreSQL, Alembic, Jinja2, and Bootstrap 5. The project supports three roles:

- `Admin` for user, vendor, membership, product, and order governance
- `Vendor` for catalog management, request visibility, and fulfillment updates
- `User` for browsing products, building carts, checking out, and tracking orders

## Features

- Session-based authentication with role-based access control
- Product catalog, cart, checkout, payment simulation, and delivery status workflow
- Membership support with delivery-fee benefits
- Server-rendered dashboards with Jinja2 and Bootstrap 5
- CSRF protection for page forms and API writes
- Input sanitization, password-strength enforcement, and file upload validation
- Alembic migration support
- Docker and Docker Compose deployment setup
- Request and runtime logging suitable for containerized deployment

## Tech Stack

- Backend: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL
- Frontend: Jinja2, Bootstrap 5
- Auth: Session cookies, bcrypt password hashing
- Validation: Pydantic
- Deployment: Docker, Docker Compose

## Project Structure

```text
app/
  api/routes/         API and page routes
  core/               config, security, csrf, logging, middleware
  crud/               focused database helpers
  db/                 SQLAlchemy base and session
  models/             ORM models
  schemas/            Pydantic schemas
  services/           business logic
  static/             css and uploaded assets
  templates/          Jinja2 templates
alembic/              database migration configuration
scripts/              container entrypoint scripts
```

## Local Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Update `.env` with:

- strong `SECRET_KEY` and `CSRF_SECRET_KEY`
- PostgreSQL credentials that match your local database
- `ALLOW_OPEN_ADMIN_SIGNUP=true` only for local bootstrap if you want to create the first admin through the signup page
- or set `ADMIN_SIGNUP_CODE` and use that during admin signup

### 4. Create the database

Create a PostgreSQL database matching the values in `.env`, then run:

```powershell
alembic upgrade head
```

### 5. Start the app

```powershell
uvicorn app.main:app --reload
```

The app will be available at:

- Application: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

## Docker Setup

### 1. Prepare environment variables

```powershell
Copy-Item .env.example .env
```

Set secure values in `.env` before exposing the stack outside your machine.

### 2. Build and run the stack

```powershell
docker compose up --build
```

This starts:

- `db`: PostgreSQL 16
- `web`: FastAPI application on port `8000`

The container entrypoint waits for PostgreSQL, runs `alembic upgrade head`, and then starts Uvicorn.

### 3. Stop the stack

```powershell
docker compose down
```

To remove volumes too:

```powershell
docker compose down -v
```

## Logging

- Application logs are emitted to stdout/stderr in a container-friendly format.
- Request logging includes method, path, status, client, and duration.
- SQL query logging can be enabled by setting `LOG_SQL_QUERIES=true`.
- Log verbosity is controlled through `LOG_LEVEL`.

## Security Notes

- Session cookies are signed and role-aware.
- CSRF protection is enforced on all state-changing forms and API endpoints.
- Passwords require uppercase, lowercase, numeric, and special characters.
- Text inputs are sanitized before use.
- Vendor image uploads are validated by extension, MIME type, file signature, and size.

## Default User Flows

- Create a `User` account to browse products, use the cart, and checkout.
- Create a `Vendor` account to submit products and process orders after admin approval.
- Create an `Admin` account using `ALLOW_OPEN_ADMIN_SIGNUP=true` or a valid `ADMIN_SIGNUP_CODE`.

## Database Migrations

Apply the current schema:

```powershell
alembic upgrade head
```

Create a new migration after future model changes:

```powershell
alembic revision -m "describe_change"
```

Then edit the generated revision and apply it:

```powershell
alembic upgrade head
```

## Important Routes

- `/login`
- `/signup`
- `/dashboard/admin`
- `/dashboard/vendor`
- `/dashboard/user`
- `/products`
- `/cart`
- `/checkout`

## Production Notes

- Set `APP_ENV=production`
- Use strong non-default secrets
- Put the app behind HTTPS and set `SESSION_HTTPS_ONLY=true`
- Disable docs in production with `SHOW_DOCS=false`
- Use managed PostgreSQL or persistent Docker volumes for data durability
