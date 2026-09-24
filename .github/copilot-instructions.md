# Copilot instructions for Filmoinator

## Build, run, and validation

Filmoinator is run as a Docker Compose stack configured by the local, untracked `stack.env` file; the repository does not currently contain an automated test suite, test runner, or lint configuration.

```bash
# Build all images
docker compose build

# Start the full stack in the background
docker compose up -d --build

# Follow application/container logs
docker compose logs -f app

# Stop the stack
docker compose down
```

The application is exposed through Nginx at `http://localhost`; the admin panel is at `/admin`. A practical smoke check after startup is `curl -I http://localhost/`. There is no single-test command at present because no tests are checked in. For a dependency-free Python syntax check, run `python -m py_compile app/app.py app/tmdb.py`.

## Architecture

- `docker-compose.yml` defines three services: PostgreSQL 16 (`db`), the Flask/Gunicorn app (`app`), and Nginx. Nginx is the only published service and proxies traffic to `app:5000`; its configuration is baked into `nginx/Dockerfile`.
- `app/app.py` contains the Flask application, SQLAlchemy models, route handlers, setup/admin authentication, voting state transitions, and database startup initialization. Gunicorn runs it as `app:app` with one worker.
- The main domain model is `Movie`, `Round`, `Vote`, `ExtraVote`, and `Result`. The administrator drives three rounds through `submission`, `voting`, `closed`, and `pending` phases. `advance_round()` records ranked results, removes non-advancing movies from the current round, and activates the next round.
- User pages are server-rendered Jinja templates. `/` handles submission, voting, interim results, and the finished winner; `/wyniki` renders the complete result history. Admin pages under `/admin` control rounds, movies, votes, settings, and a projector-oriented `/admin/widok` view.
- `app/tmdb.py` is the only TMDB integration layer. It performs movie search, details, and age-rating requests with a five-second timeout and returns empty results/strings (or `None` for details) when TMDB requests fail.
- Runtime configuration comes from `stack.env` through Compose `env_file`: `ADMIN_PASSWORD`, `TMDB_API_KEY`, `QR_URL`, and database settings. Flask generates a random session key at startup unless `SECRET_KEY` is explicitly provided. The `vote_per_ip` setting is stored in PostgreSQL and changed from `/admin/settings`. PostgreSQL data is stored in the named `postgres_data` volume; no host directories are mounted into the stack.
- On every app startup, `db.create_all()` is followed by `migrate_db()` and `ensure_rounds()`, which add later columns/remove the original one-vote uniqueness constraint and seed the three rounds. Keep schema changes compatible with this startup path.

## Repository conventions

- User-facing text and template content are Polish; preserve Polish labels and flash messages when changing user flows.
- Keep business logic in the existing Flask/SQLAlchemy style in `app/app.py` and use the model classes/query helpers rather than introducing a second persistence layer.
- User identity for voting is the long-lived `visitor_id` cookie. The normal limit is one vote per round and is extended through `ExtraVote`; optional IP-based blocking is controlled by the admin setting `vote_per_ip` and uses forwarded client IP headers.
- Admin mutations are POST routes protected by `@admin_required`, followed by a database commit, a categorized `flash()`, and a redirect. Preserve this pattern for new admin actions.
- There is no browser setup/settings flow. TMDB tokens and other operational settings are supplied from environment variables to `tmdb.py`; do not hard-code credentials or move them into tracked files. The values in `stack.env.example` are development placeholders and must be replaced locally.
- Templates use inline CSS and JavaScript with shared public styling/behavior in `app/templates/base.html`; admin templates are standalone pages with their own inline styles. Preserve the existing server-rendered Jinja flow when adding UI.
- The UI displays device IDs derived from the first four characters of `visitor_id`, while the admin vote view exposes vote metadata such as IP address and user agent. Treat these fields as part of the existing operational/admin workflow.
