# photos-by-date

Sorts photos into `YYYY/MM/` folders using EXIF capture date, falling back to
file modification time. Stdlib only, no `pip install`, no API key.

Built with [skill-lint](https://github.com/<your-name>/skill-lint) — scores 90+.

## Install

```bash
cp -r photos-by-date ~/.claude/skills/
```

## Usage

Ask your agent:

> Sort these photos into folders by date.

Or run it directly:

```bash
python scripts/sort_photos.py ~/Photos --dry-run    # preview
python scripts/sort_photos.py ~/Photos              # move
python scripts/sort_photos.py ~/Photos --recursive  # include subfolders
```

```
Moved 128 files into 11 folders.
Skipped 3 files: no EXIF and no readable mtime.
```

## Safety

- `--dry-run` prints the plan and moves nothing — run it first.
- Files whose date cannot be determined are listed, never moved.
- Nothing is deleted; files are moved only.

## License

MIT
