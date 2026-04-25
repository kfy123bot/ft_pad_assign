# CLAUDE.forGit.md

Git & GitHub quick reference for Claude Code.

---

## Repository Info

| Item | Value |
|------|-------|
| Account | `kfy123bot` |
| Email | `kfy123.bot@gmail.com` |
| SSH URL | `git@github.com:kfy123bot/fpad_assign.git` |
| Main branch | `main` |

---

## Quick Start (New Directory)

```bash
git clone git@github.com:kfy123bot/fpad_assign.git
cd fpad_assign
git config user.email "kfy123.bot@gmail.com"
git config user.name "kfy123bot"
```

Done. No password needed.

---

## Daily Commands

```bash
# Pull latest
git pull

# Check status
git status

# View commits
git log --oneline -5

# Commit and push
git add <files>
git commit -m "type: description"
git push
```

---

## Commit Format

```
<type>: <description>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `perf`, `chore`, `test`, `ci`

**Examples:**
```bash
git commit -m "fix: Fix B side label truncation"
git commit -m "docs: Add GitHub guide"
git commit -m "feat: Add ground symbol support"
```

---

## Safety Checklist Before Push

- [ ] `git diff` — reviewed changes
- [ ] No hardcoded tokens/keys/passwords
- [ ] Commit message follows format
- [ ] Tests pass (`make test_py`)

```bash
git push origin main
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| SSH connection fails | `ssh -T git@github.com` to diagnose |
| Wrong branch | `git branch -a` then `git checkout main` |
| Need to undo commit | `git reset --soft HEAD~1` (keep changes) |
| Forgot to add file | `git add <file>` then `git commit --amend --no-edit` |

---

## Reference

- **Full docs**: `~/.claude/memory/github_fpad_assign_setup.md`
- **Project guide**: `CLAUDE.md`
- **Bug analysis**: `tobefix.md`
