# Gitfleet

Gitfleet is a fast command-line tool for managing a directory of Git repositories as a fleet.

It scans the configured project root, exposes repositories through current inventory numbers, reports Git metadata and status, performs guarded updates and pushes, restores missing repositories from a manifest, and creates compressed backups for an rclone remote.

## Requirements

- Python 3.12+
- Git
- uv
- rclone
- GNU tar
- zstd
- glow (optional, for viewing reports)

## Setup

Install the environment:

```bash
uv sync
```

Run Gitfleet:

```bash
uv run gitfleet --help
```

The repository also includes `gitfleet.sh` as a convenience launcher.

## Configuration

Gitfleet reads `~/.config/gitfleet/config.toml` by default. If `XDG_CONFIG_HOME` is set, it uses `$XDG_CONFIG_HOME/gitfleet/config.toml`.

```toml
[paths]
scan_root = "/mnt/.data/local/projects"
clone_root = "/mnt/.data/local/projects"
report = "reports/projects.md"

[backup]
remote = "gdrive:backups/projects"
format = "tar.zst"
```

`scan_root` contains the direct child Git repositories managed by Gitfleet.

`clone_root` is the destination used when restoring missing repositories.

The backup destination uses rclone remote syntax.

## Commands

List the current project inventory:

```bash
gitfleet list
```

`list` scans every real direct child directory under `scan_root`, including hidden directories. Symlinks are ignored.

The summary shows the total number of direct directories, Git repositories, and non-Git directories. Non-Git directories are listed separately before the Git repository inventory.

A directory is considered a Git repository when it contains a `.git` directory or `.git` file. A GitHub, GitLab, Codeberg, or other remote is not required. Git inventory numbers remain assigned only to Git repositories.

Show Git metadata for a repository:

```bash
uv run gitfleet show 12
```

Check local and remote status:

```bash
uv run gitfleet status 12
```

Use cached remote refs without fetching:

```bash
uv run gitfleet status 12 --no-fetch
```

Safely fast-forward a repository:

```bash
uv run gitfleet update 12
```

Safely push committed local changes:

```bash
uv run gitfleet push 12
```

Generate the Markdown project report:

```bash
uv run gitfleet report
```

View the generated report with glow:

```bash
uv run gitfleet report --view
```

Preview repository restoration:

```bash
uv run gitfleet clone --dry-run
```

Restore missing repositories:

```bash
uv run gitfleet clone
```

Set parallel clone concurrency:

```bash
uv run gitfleet clone --workers 8
```

Validate backup configuration without creating or uploading an archive:

```bash
uv run gitfleet backup --dry-run
```

Create and upload a backup:

```bash
uv run gitfleet backup
```

## Clone states

The clone plan uses four states:

- `CLONE` — the repository is missing and can be restored.
- `SKIP` — the repository already exists.
- `CONFLICT` — the target exists but conflicts with the expected repository.
- `NO ORIGIN` — no usable origin is available for restoration.

## Safety

Gitfleet avoids destructive or ambiguous Git operations in its normal workflow.

`update` performs guarded updates instead of arbitrary merges.

`push` operates on already committed local changes.

`clone --dry-run` shows the restoration plan without cloning anything.

`backup --dry-run` validates the backup configuration and required tools without creating an archive or uploading data.

## Generated files

The Markdown report is written to the path configured in `config.toml`.

Repository restoration uses:

```text
reports/repositories.json
```

Generated reports and repository manifests are ignored by Git.

## Tests

Run the complete test suite:

```bash
uv run pytest -q
```

## Version

Current version: `0.1.0`