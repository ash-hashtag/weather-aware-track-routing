# Weather-Aware Truck Routing

React + Django app that helps a truck driver choose the safest route based on weather,
load weight, and travel time. See [`fs-assessment-spotter.pdf`](./fs-assessment-spotter.pdf)
for the full brief.

## Stack

| Part       | Tech                                                        |
| ---------- | ----------------------------------------------------------- |
| `frontend` | React 19, TypeScript (strict), Vite, pnpm, oxlint           |
| `backend`  | Python 3.14, Django + DRF, uv, mypy (strict + django-stubs), ruff, pytest |

## Getting started

Prerequisites: Node 22+, pnpm, [uv](https://docs.astral.sh/uv/).

```sh
cp .env.example .env

# Backend — http://127.0.0.1:8000
cd backend
uv sync
uv run python manage.py runserver

# Frontend — http://localhost:5173 (proxies /api → :8000)
pnpm install
pnpm dev
```

## Checks

```sh
# frontend
pnpm typecheck && pnpm lint && pnpm build

# backend (from ./backend)
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
```

## Domain rules (from the brief)

**Weather risk per checkpoint**

| Condition | Low         | Moderate  | High      | Severe    | No Travel |
| --------- | ----------- | --------- | --------- | --------- | --------- |
| Wind      | <25 mph     | 25–34     | 35–44     | 45–54     | ≥55 mph   |
| Rain      | <0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | >1.00     |
| Snow      | <0.5 in/hr  | 0.5–1.0   | 1.0–2.0   | 2.0–3.0   | >3.0      |

**Load rules**

- ≥55 mph → No Travel for any load
- 45–54 mph + >30,000 lb → No Travel
- 35–44 mph + >40,000 lb → Severe

**Recommendation order:** fewest Severe miles → fewest High miles → lowest average risk →
shortest travel time.

Weather is sampled every 10 / 25 / 50 miles at the truck's ETA for each checkpoint.
