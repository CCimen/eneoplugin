---
description: Point the Eneo dev database at the current git branch, or inspect and prune per-branch databases
argument-hint: "[switch|status|prune|fork <name>] [--base <branch>] [-y]"
allowed-tools:
  - Bash(eneo-dev-db)
  - Bash(eneo-dev-db *)
  - Bash(git branch *)
  - Bash(git status *)
---

Run `eneo-dev-db` with the arguments the user gave: `$ARGUMENTS`.

If no arguments were given, run `eneo-dev-db status` first and report what it
says. Only run `switch` after that if the report shows a mismatch (`backend/.env`
pointing at a different branch's database, or the branch having no database yet),
and say what it will clone from before doing it.

Pass `-y` when running unattended, since `switch` otherwise blocks on a
confirmation prompt when it needs to create a database.

Never edit `backend/.env` directly. It is denied to file tools and blocked to
shell redirects. The tool owns that file.

Ignore any `scripts/dev-db-init.sh` or `scripts/dev-db-commit.sh` in the
repository. Those implement a superseded model that swaps database contents in
and out of one shared database, and running them will overwrite state.

After a successful `switch`, remind the user that the backend and worker need a
restart, and do not start them yourself.
