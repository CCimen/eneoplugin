---
name: eneo-dev-db
description: Use whenever the Eneo dev database needs to follow the git branch, for example after checking out or creating a branch, when the app or a query fails with UndefinedColumn/UndefinedTable/"relation does not exist", when data looks like it belongs to a different branch, when alembic wants a downgrade after a branch switch, or when the devcontainer Postgres is eating disk. Every branch owns a database named eneo_<sanitized-branch>. The eneo-dev-db tool is the only sanctioned way to change POSTGRES_DB, which you cannot read or edit directly.
---

# eneo-dev-db

In the Eneo repo, every git branch owns a real Postgres database,
`eneo_<sanitized-branch>`. A new branch's database is cloned once from the branch
it was created from; after that, switching branches only repoints `POSTGRES_DB`
in `backend/.env`. Nothing is copied on a switch and no branch's data is ever
overwritten.

## Invoking it

The tool ships with this plugin, so it works from every branch, including ones
that carry no dev-db tooling of their own. It acts on whichever repository the
working directory is inside.

```bash
eneo-dev-db status
```

The plugin's `bin/` directory is on the Bash tool's PATH while the plugin is
enabled, so call `eneo-dev-db` and `eneo-mig-sim` by bare name. They work from
the host and from inside the devcontainer: containers are discovered from the
running compose project, so do not wrap them in `docker exec` or `eneo-exec`.

**Ignore `scripts/dev-db-init.sh` and `scripts/dev-db-commit.sh`** if you find
them in the repo. They implement a superseded model that swaps database contents
in and out of one shared database and assumes `POSTGRES_DB` never changes.
Running `dev-db-init.sh` will overwrite whichever database `.env` points at.

## Commands

| Command | Use it for |
|---|---|
| `status` | Branch, its database and size, what `.env` actually points at, the base branch, alembic revision vs repo head |
| `switch` | Create the branch database if missing, repoint `.env`, run `alembic upgrade head` |
| `switch --base <branch>` | Override which branch to clone from (only matters on first creation) |
| `switch --no-migrate` | Same, but skip alembic |
| `prune` | List databases whose branch is gone; add `--yes` to drop them |
| `fork <name>` | Scratch copy of the current branch's database before something destructive |

Add `-y` to skip confirmations. Without it, `switch` blocks on a prompt when it
needs to create a database, so always pass `-y` when running unattended.

## Rules

**Never touch `backend/.env` yourself.** The Eneo harness denies reading it,
`protect-files.sh` blocks editing it, and the bash firewall blocks shell
redirects at it. The tool owns that file. This also means `status` is your only
way to see which database is live: run it before and after a `switch` rather
than assuming.

**A switch kicks the Postgres connection**, so the backend and worker need a
restart afterwards. The tool prints the exact command. Do not restart them
yourself: report the command and let the developer do it.

**Do not hand-roll psql against a branch database** to patch a schema mismatch.
The right move is `switch` (which runs `alembic upgrade head`), or `fork` first
if the state is precious.

## Diagnosing

Run `status` first. It distinguishes:

- *`backend/.env` does not match this branch*: the branch was switched without
  running `switch`. This is the usual cause of missing columns and stale data.
- *database does not exist*: new branch, never switched to. `switch` creates it;
  check the reported base branch before confirming.
- *alembic revision differs from repo head*: `switch` fixes an out-of-date
  database. A database **ahead** of the repo is normal and harmless: it was
  cloned from a branch carrying extra migrations, and those tables go unused
  here.

## First run in a checkout

A checkout that has never used this tool has `POSTGRES_DB` pointing at a
database without the `eneo_` prefix (`postgres` by default). On the first
`switch`, the tool offers to seed the branch database from that active database
instead of from the base branch, because that is where the developer's existing
data lives. Do the first `switch` on `develop`, so `eneo_develop` exists as the
baseline every later branch can clone from.

## Base branch resolution

On first creation only, first match wins: `--base`, then
`git config branch.<name>.eneoDbBase`, then the branch this one was created from
per its reflog, then the nearest ancestor branch that has a database, then
`develop`. Candidates without a database are skipped, since there would be
nothing to clone. The choice is recorded in git config, so a wrong guess is
fixable with `git config branch.<name>.eneoDbBase <correct>`, dropping the
database, and re-running `switch`.

For a branch stacked on another feature branch, the parent must have been
switched to at least once for its schema to be inherited.

## Migration simulation (eneo-mig-sim)

`eneo-mig-sim` rehearses upgrade paths between releases against throwaway
databases (`eneo_migsim_*`), without touching any branch database or
`backend/.env`. It extracts a git ref's `backend/` with `git archive` into
`.mig-sim/` inside the repo (visible to the devcontainer), gives it its own uv
environment and a private `.env` copy pointing at the scratch database, and runs
that ref's alembic. Use it to answer questions like "what happens to a v2.0.1
database when v2.1.0-rc.1's migrations run against it?".

| Command | Use it for |
|---|---|
| `create <name>` | Fresh empty scratch db `eneo_migsim_<name>` (drops any existing one) |
| `alembic <name> <git-ref> <args...>` | Run `<git-ref>`'s alembic against the scratch db, e.g. `alembic broken v2.0.1 upgrade head` |
| `clone <src> <dest>` | Copy a scratch db (e.g. snapshot a broken state before testing repairs) |
| `sql <name> <SQL>` | Inspect or mutate a scratch db (fine here, unlike branch dbs) |
| `dump <name>` | `pg_dump --schema-only` to stdout, for schema diffing between paths |
| `drop <name>` / `clean` | Drop one / all scratch dbs (`clean` also removes `.mig-sim/`) |

The first `alembic` call for a ref builds its uv environment (a minute or two);
later calls are fast. Migrations that call external services run with whatever
network the devcontainer has.

**Extracted trees are cached by ref name and never refreshed.** A tag is safe.
A moving ref (`HEAD`, a branch name) keeps running the tree from the first time
it was extracted, which shows up as failures that do not match the current
code. Pass a commit sha (`git rev-parse --short HEAD`) for anything that moves,
or remove `.mig-sim/<name>` before reusing the name.

**`clean` drops every `eneo_migsim_*` database**, including snapshots the
developer made by hand with `clone`. Prefer `drop <name>` for the databases you
created, and only run `clean` when asked.

`check-v21-upgrade` composes these into the release-validation suite for the
v2.1 migration-repair guidance (reproduces the v2.0.1 → v2.1.0-rc.1 skip bug,
checks the published and surgical repairs, direct and fresh paths, and schema
equivalence). `V21_REF=<ref>` overrides the v2.1 ref (default `release/v2.1`).

## Scope

Only Postgres is per-branch. Redis is shared, so ARQ jobs queued on one branch
run against whichever database is active when the worker picks them up. Object
storage is shared too. This tooling is specific to the Eneo repo and its
devcontainer compose project; it does nothing useful elsewhere.
