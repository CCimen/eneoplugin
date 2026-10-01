# eneo-dev-db

Per-branch development databases for the Eneo devcontainer Postgres.

Every git branch owns a real database named `eneo_<sanitized-branch>`. A branch's
database is created once by cloning the database of the branch it was created
from. After that, switching branches only repoints `POSTGRES_DB` in
`backend/.env`. Nothing is copied on a switch, so there is no save step and no
way to lose a branch's data by forgetting one.

This lives in a plugin rather than in the Eneo repo on purpose: a tracked script
only exists on the branch that carries it, which is useless precisely when you
switch to a branch that does not. The plugin works from every branch, including
ones that predate it.

## Install

```bash
/plugin install eneo-dev-db@eneoplugin
/reload-plugins
```

The plugin is optional and independent of the other Eneo plugins. It gives
Claude the `eneo-dev-db` skill, the `/eneo-dev-db:dev-db` command, and the tools
in `bin/` on the Bash tool's PATH.

For use from your own terminal, link the tools into a directory on your PATH.
`eneo-mig-sim` and `check-v21-upgrade` look for their siblings next to
themselves, so link all three into the same place:

```bash
for tool in eneo-dev-db eneo-mig-sim check-v21-upgrade; do
  ln -sf ~/.claude/plugins/marketplaces/eneoplugin/plugins/eneo-dev-db/bin/$tool ~/.local/bin/$tool
done
```

## Use

```bash
eneo-dev-db switch     # create if needed, repoint .env, alembic upgrade head
eneo-dev-db status     # branch, database, size, base, alembic revision
eneo-dev-db prune      # list databases whose branch is gone (--yes to drop)
eneo-dev-db fork NAME  # scratch copy before something destructive
```

Run it from anywhere inside the Eneo checkout; it acts on the repository your
working directory is in. `-y` skips confirmation prompts.

`switch` kicks the backend's Postgres connection, so restart the backend and
worker afterwards. The exact command is printed. Containers are discovered from
the running compose project, so no names are hardcoded, and the tool works from
the host as well as from inside the devcontainer.

## First run

A fresh checkout has `POSTGRES_DB=postgres`, which is not a per-branch database.
Check out `develop` and run:

```bash
eneo-dev-db switch
```

The tool notices that the active database predates it and offers to seed
`eneo_develop` from it, so the data you already have carries over. Say yes.
From then on `eneo_develop` is the baseline that new branches clone from, and
the original `postgres` database is left untouched.

## Which branch does a new one clone from?

First match wins:

1. `--base <branch>`
2. `git config branch.<name>.eneoDbBase`
3. the branch this one was created from, per its git reflog
4. the nearest ancestor branch that already has a database
5. `develop`

Rules 3 and 4 skip candidates with no database, since there would be nothing to
clone. The result is recorded in git config:

```bash
git config branch.$(git branch --show-current).eneoDbBase
```

For a branch stacked on another feature branch, the parent must have been
switched to at least once for its schema to be inherited.

## Superseded scripts

The Eneo repo carries `scripts/dev-db-init.sh` and `scripts/dev-db-commit.sh`.
They implement the previous model, where snapshot contents were swapped in and
out of one shared active database, and they assume `POSTGRES_DB` is a fixed
name. Do not run them alongside this tool: `dev-db-init.sh` will overwrite
whichever database `.env` currently points at.

## Rehearsing migrations: eneo-mig-sim

`eneo-mig-sim` runs any git ref's alembic against throwaway `eneo_migsim_*`
databases, without touching a branch database or `backend/.env`. Use it to
rehearse an upgrade path between releases before it reaches a real install.

```bash
eneo-mig-sim create broken                         # empty scratch database
eneo-mig-sim alembic broken v2.0.1 upgrade head    # run v2.0.1's migrations
eneo-mig-sim alembic broken v2.1.0-rc.1 upgrade head
eneo-mig-sim clone broken repair-attempt           # snapshot before a repair
eneo-mig-sim sql broken "SELECT version_num FROM alembic_version;"
eneo-mig-sim dump broken > broken.sql              # schema only, for diffing
eneo-mig-sim drop broken
```

Each ref's `backend/` is extracted once with `git archive` into `.mig-sim/` in
the checkout (added to `.git/info/exclude`) and gets its own uv environment, so
the first run for a ref takes a minute or two.

Two things to know:

- Extracted trees are cached by ref name and never refreshed. Tags are safe.
  For `HEAD` or a branch name, pass a commit sha instead, or delete
  `.mig-sim/<name>` first.
- `eneo-mig-sim clean` drops every `eneo_migsim_*` database and removes
  `.mig-sim/`, including scratch databases you wanted to keep.

`check-v21-upgrade` is a worked example built on it: the validation suite for
the v2.1 migration-repair guidance. It reproduces the v2.0.1 → v2.1.0-rc.1
migration-skip bug, checks the published and the surgical repair, the direct
and fresh-install paths, and asserts the repaired schema equals the
direct-upgrade schema. `V21_REF=<ref>` overrides the v2.1 ref (default
`release/v2.1`).

## What is not isolated per branch

Only Postgres. Redis is shared, so ARQ jobs queued on one branch run against
whichever database is active when the worker picks them up. Object storage is
shared too, though the `object-content` compose service is off by default.

Branch names are sanitized by lowercasing and dropping every character outside
`[a-z0-9_]`, with `/` mapped to `_`. Hyphens are deleted rather than mapped, so
`feat/foo-bar` and `feat/foobar` would collide on one database. The tool refuses
names that sanitize to nothing or exceed Postgres's 63-character identifier
limit.

## Tests

From the root of this repository:

```bash
python3 -m unittest tests.test_dev_db
```

17 tests covering name sanitizing, the `.env` read/write path, and base-branch
resolution. They source the script and stub the database list, so no Docker or
Postgres is needed.
