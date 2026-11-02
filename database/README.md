# ID Colis database setup

1. Install and start local MySQL.
2. Run `schema.sql` as an administrator.
3. Set `IDCOLIS_DATABASE_URL` using the credentials for the new database.
4. Start the API with `python -m backend.serve`; the application creates the baseline tables.
5. Run the seed flow on first startup to create the demo roles, teams, users, and logistics training data.

For production, use Alembic migrations instead of relying on automatic table creation.

