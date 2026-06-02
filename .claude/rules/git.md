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
```

## Development workflow

**Never commit directly to `main`.** Always work on feature branches.

```bash
# 1. Start from latest main
git checkout main
git pull origin main

# 2. Create a short-lived feature branch
git checkout -b feature/<name>
# or: git checkout -b fix/<name>

# 3. Work, commit incrementally, push to personal
git push -u personal feature/<name>

# 4. When ready, PR from personal/feature/<name> → origin/main
# 5. After merge, delete the branch
git checkout main
git pull origin main
git branch -d feature/<name>
```

### Branch naming

```
feature/<short-description>   → feature/edp-agent-integration
fix/<short-description>       → fix/rollout-timeout
refactor/<short-description>  → refactor/adapter-pattern
test/<short-description>      → test/edp-smoke
docs/<short-description>      → docs/api-reference
chore/<short-description>     → chore/update-deps
```

### Push targets

| What | Push to |
|------|---------|
| Feature branches | `personal` (your fork) |
| `main` | **Never push directly** — only via PR merge from upstream |

### Oops: committed to main

If you accidentally commit to `main`, move the commits to a feature branch and reset:

```bash
# 1. Create feature branch from current HEAD (saves your work)
git branch feature/<name>

# 2. Reset main back to upstream
git reset --hard origin/main

# 3. Continue on the feature branch
git checkout feature/<name>
git push -u personal feature/<name>

# 4. If you already pushed to personal/main, force-revert it
git push personal origin/main:main --force
```

## Before committing

- Run `ruff check` and `ruff format`
- Verify no secrets: `git diff --staged | grep -i "api_key\|password\|secret\|token"`
- Never commit `.env`, `.secrets/`, `**/*.local.*`, `**/*.secret.*` (covered by `.gitignore`)

## Generated files to NOT commit

These are covered by `.gitignore`: `__pycache__/`, `*.pyc`, `build/`, `dist/`, `outputs/`, `data/`, `logs/`, `.understand-anything/`, `docs/handoff/`.

## Branching

Work on short-lived feature branches off `main`, merge within 1-3 days. Delete branches after merge.

- **Keep `main` clean** — it should always match `origin/main` and be deployable.
- **One feature per branch** — don't bundle unrelated changes.
- **Rebase, don't merge** — when pulling upstream changes into your feature branch, use `git rebase main` to keep history linear.
