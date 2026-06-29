## Project context

This repository contains the website described in `docs/prd.md`.

Before making product or implementation decisions, read:

- `docs/prd.md` for product requirements
- `docs/roadmap.md` for build order and priorities
- `docs/features.md` for feature-level behavior and acceptance criteria
- `docs/decisions.md` for previous decisions and rationale

## Working rules

- Do not invent requirements that are not documented.
- If something is unclear, make a reasonable assumption and record it in `docs/decisions.md`.
- Keep `docs/roadmap.md` updated when implementation order changes.
- Update documentation when product behavior, roadmap order, or technical decisions change.
- Prefer small, focused, and reviewable commits.
- Run the relevant lint/test/build commands before considering work done.

## Documentation rules

- Update `docs/roadmap.md` when task status or priority changes.
- Update `docs/features.md` when feature behavior, edge cases, or acceptance criteria change.
- Update `docs/decisions.md` when an important product, design, or technical decision is made.
- Do not treat chat history as the source of truth; the repo docs are the source of truth.

## Before coding

For any non-trivial feature:

1. Read the relevant docs.
2. Propose a short implementation plan.
3. Identify files that will likely change.
4. Confirm assumptions in `docs/decisions.md` if needed.

## Definition of done

A task is done when:

- The implementation matches the documented requirements.
- Relevant docs are updated.
- The app runs locally.
- The code is committed on a feature branch.
- Tests, linting, or build checks pass if available.
- Known limitations or follow-up tasks are documented.