# FoodFind

FoodFind is a web application for discovering places to get food near a selected location. The Python FastAPI backend serves normalized place APIs; the SvelteKit frontend provides the browser interface. Current build status and next work are tracked in [`docs/roadmap.md`](docs/roadmap.md).

## Setup

Requires Python 3.10 or newer and Node.js `^20.19.0` or `>=22.12.0`.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## Google Places setup

Google integration is server-side only. Add the key to `.env`:

```text
GOOGLE_MAPS_API_KEY=your-key
```

Current local-development setup:

- Restrict the key to **Places API** and **Places API (New)** in Google Cloud.
- Keep the key in `.env`; do not put it in browser code, committed files, logs, or test fixtures.
- Set a low billing budget alert. The current alert is `$2/month`.

A daily quota is preferred before broader live testing. If Google Cloud does not allow quota changes during the free trial, keep live requests manual and sparse until quota controls are available. Automated tests use mocked responses and do not require a key or call Google.

Location autocomplete and selection use **Places API (New)**, so the existing API restriction covers them; no additional Google API needs to be enabled for Phase 2 Step 1B.

To make one controlled live request for local verification:

```sh
python -m app.scripts.google_places_smoke
```

Do not add this command to automated tests.

## Run

Run the backend and frontend in separate terminals:

```sh
fastapi dev app/main.py
```

```sh
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>. The frontend development server proxies `/api` to FastAPI at <http://127.0.0.1:8000>. The older page at port `8000` remains only as a temporary migration fallback.

## Test

```sh
pytest
```

Frontend checks:

```sh
cd frontend
npm run check
npm run test:unit -- --run
npx playwright install chromium
npm run test:e2e
npm run build
```

Frontend tests intercept or mock FoodFind API responses and never call Google.

## Project documentation

- [`docs/prd.md`](docs/prd.md): product requirements
- [`docs/roadmap.md`](docs/roadmap.md): build order and status
- [`docs/features.md`](docs/features.md): feature behavior
- [`docs/decisions.md`](docs/decisions.md): product and technical decisions
- [`docs/concepts.md`](docs/concepts.md): implementation concepts explained
- [`docs/phase-1-overview.md`](docs/phase-1-overview.md): Phase 1 architecture and file-by-file walkthrough
