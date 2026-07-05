# FoodFind

FoodFind is a web application for discovering places to get food near a selected location. The project is currently implementing Phase 1 from [`docs/roadmap.md`](docs/roadmap.md).

## Setup

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

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
