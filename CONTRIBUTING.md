# Contributing

This project is developed as a collaborative research and engineering repo for a physical-consistency image editing agent.

## Collaboration Workflow

Do not push directly to `main` for normal development. Use a feature branch for each unit of work:

```powershell
git checkout main
git pull origin main
git checkout -b feature/short-task-name
```

Commit focused changes with a clear message:

```powershell
git status
git add <changed-files>
git commit -m "Describe the change"
git push -u origin feature/short-task-name
```

Open a pull request into `main` and describe:

- what changed
- why it changed
- how it was tested
- any known limitations or follow-up work

## Repository Rules

- Keep `.env` local. Never commit API keys, tokens, service credentials, or private endpoint secrets.
- Use `.env.example` for configuration templates.
- Prefer small, reviewable pull requests over large mixed changes.
- Keep generated experiment artifacts out of Git unless they are deliberate reports, summaries, or figures needed for documentation.
- Do not commit local cache files, temporary Office lock files, Python caches, logs, or ad hoc API probe outputs.
- Preserve existing user work. Do not rewrite, delete, or revert someone else's changes without explicit agreement.

## Development Notes

Core agent code lives under `src/physical_agent`.

Main entry points:

- `run_agent.py` for the MVP agent loop.
- `scripts/run_picabench_examples.py` and `scripts/run_picabench_resumable.py` for dataset runs.
- `docs/` for design notes, evaluation reports, and development planning.

Before opening a pull request, run the most relevant smoke test or script for the area changed. If a test cannot be run because it requires paid API calls or local credentials, state that clearly in the pull request.

## Branch Protection Recommendation

For the GitHub repository, protect `main` with:

- pull request required before merge
- no force pushes
- no branch deletion
- at least one review for substantial changes

This keeps the GitHub remote as the shared backup and the stable source of truth.
