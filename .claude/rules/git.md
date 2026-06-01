# Git Conventions

## Commit messages

Follow the conventional commits format:

```
<type>: <short description>

<optional body explaining why, not what>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

## Remote layout

- `origin` → `microsoft/SkillOpt` (upstream)
- `personal` → `xuzixuan1998/SkillOpt` (your fork)

```bash
git pull origin main          # sync from upstream
git push personal main        # push to your fork
```

## Before committing

- Run `ruff check` and `ruff format`
- Verify no secrets: `git diff --staged | grep -i "api_key\|password\|secret\|token"`
- Never commit `.env`, `.secrets/`, `**/*.local.*`, `**/*.secret.*` (covered by `.gitignore`)

## Generated files to NOT commit

These are covered by `.gitignore`: `__pycache__/`, `*.pyc`, `build/`, `dist/`, `outputs/`, `data/`, `logs/`, `.understand-anything/`, `docs/handoff/`.

## Branching

Work on short-lived feature branches off `main`, merge within 1-3 days. Delete branches after merge.
