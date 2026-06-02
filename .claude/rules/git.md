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

## Branch layout

```
personal fork (xuzixuan1998/SkillOpt)
├── main   = origin/main      ← 只从 upstream 同步，绝不直接提交
├── dev                        ← 集成分支，feature 合并到这里
└── feature/<name>             ← 具体功能分支（短期，1-3天）
```

## Development workflow

**Never commit directly to `main`.** Feature branches → `dev` → PR to upstream.

```bash
# 1. Sync main from upstream
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feature/<name>

# 3. Work, commit incrementally, push to personal
git push -u personal feature/<name>

# 4. When done, merge into dev on personal fork
git checkout dev
git pull origin main              # sync dev with upstream first
git merge feature/<name>          # fast-forward if possible
git push personal dev

# 5. Create PR from personal/dev → origin/main on GitHub
#    https://github.com/xuzixuan1998/SkillOpt/pull/new/dev

# 6. After PR merged upstream, clean up
git checkout main
git pull origin main
git branch -d feature/<name>
git push personal --delete feature/<name>
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
| `feature/<name>` | `personal` (your fork) |
| `dev` | `personal` (your fork) |
| `main` | **Never push** — only sync from `origin/main` |

### Oops: committed to main

If you accidentally commit to `main`, move the commits to a feature branch and reset:

```bash
# 1. Create feature/dev branch from current HEAD (saves your work)
git branch feature/<name>

# 2. Reset main back to upstream
git reset --hard origin/main

# 3. Continue on the feature branch
git checkout feature/<name>
git push -u personal feature/<name>

# 4. If you already pushed to personal/main, force-revert it
git push personal origin/main:main --force

# 5. If dev was affected, recreate it from main + feature
git checkout main
git checkout -B dev
git merge feature/<name>
git push personal dev --force
```

## Before committing

- Run `ruff check` and `ruff format`
- Verify no secrets: `git diff --staged | grep -i "api_key\|password\|secret\|token"`
- Never commit `.env`, `.secrets/`, `**/*.local.*`, `**/*.secret.*` (covered by `.gitignore`)

## Generated files to NOT commit

These are covered by `.gitignore`: `__pycache__/`, `*.pyc`, `build/`, `dist/`, `outputs/`, `data/`, `logs/`, `.understand-anything/`, `docs/handoff/`.

## Branching

Three kinds of branches on the personal fork:

| Branch | Role | Lifetime |
|--------|------|----------|
| `main` | Mirror of `origin/main` | Permanent |
| `dev` | Integration branch, all features land here before PR | Permanent |
| `feature/*` | Single feature, short-lived | 1-3 days, delete after merge |

- **Keep `main` clean** — never push to it, only `git pull origin main`.
- **`dev` is the PR source** — merge completed features into `dev`, then PR `dev` → `origin/main`.
- **One feature per branch** — don't bundle unrelated changes.
- **Sync `dev` from `main`** — before merging a feature, `git checkout dev && git pull origin main`.
