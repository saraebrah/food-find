# FoodFind

FoodFind is a web application for discovering places to get food near a selected location. The project is currently implementing Phase 1 from [`docs/roadmap.md`](docs/roadmap.md).

## Setup

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Google Places setup

Google integration is server-side only. Add the key to `.env`:

```text
GOOGLE_MAPS_API_KEY=your-key
```

Before making live requests, configure a low daily Places API quota in Google Cloud. Automated tests use mocked responses and do not require a key or call Google.

## Run

```sh
fastapi dev app/main.py
```

Open <http://127.0.0.1:8000>.

## Test

```sh
pytest
```

## Project documentation

- [`docs/prd.md`](docs/prd.md): product requirements
- [`docs/roadmap.md`](docs/roadmap.md): build order and status
- [`docs/features.md`](docs/features.md): feature behavior
- [`docs/decisions.md`](docs/decisions.md): product and technical decisions
