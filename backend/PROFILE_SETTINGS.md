# Profile settings and administrator access

The profile API is available at `/api/profile`. Profile read and update operations use the authenticated bearer token and always operate on that account. Theme preference read/update is at `/api/profile/theme` and is stored for the authenticated account. Profile photo reads are private and require the owner's bearer token. Photo upload/removal is restricted to accounts whose database `role` is `admin`.

## Apply the schema change

For production PostgreSQL, back up the database and run the existing Alembic migration chain:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
```

The repository's local SQLite development database has no Alembic revision recorded and the older SQLite migration chain is not compatible with the integration-constraint migration. For that specific development database, run this guarded additive updater instead:

```powershell
cd backend
python -m scripts.add_profile_preferences_sqlite
```

It refuses non-development/non-SQLite databases and only adds missing account columns; it does not modify existing account values.

Existing accounts receive the `user` role. No account is automatically promoted. To explicitly promote an already registered account, set `AURA_ALLOW_ADMIN_ROLE_CHANGE=YES` for that invocation and run:

```powershell
$env:AURA_ALLOW_ADMIN_ROLE_CHANGE = "YES"
python -m scripts.set_user_role admin@example.com --role admin --confirm
Remove-Item Env:AURA_ALLOW_ADMIN_ROLE_CHANGE
```

The command changes only the named account's role; it does not create accounts or set passwords. The earlier `admin/admin` credential pair is not provisioned.

## Photo storage

Development photos are stored under `backend/private_uploads/profile_photos/`, outside the frontend's public directory. Requests are bounded to 5 MiB and validated by image signature; filenames are randomly generated. Do not expose this directory through a static web server. This filesystem storage is suitable for local development or a single persistent backend instance. Multi-instance/production deployment should configure private object storage with equivalent access controls and lifecycle cleanup.
