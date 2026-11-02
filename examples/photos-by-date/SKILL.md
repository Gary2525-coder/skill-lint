---
name: photos-by-date
description: Renames and sorts photo files into YYYY/MM folders using EXIF capture date, falling back to file mtime when EXIF is absent. Use when the user asks to organise, rename, or sort photos by the date they were taken.
license: MIT
---
# photos-by-date

## When to use

- "Sort these photos into folders by date."
- "Rename my images so they sort chronologically."
- "按拍摄日期整理这些照片"

## Workflow

1. **Scan** — run `python scripts/sort_photos.py <dir> --dry-run` and report the count.
2. **Confirm** — show the proposed tree; ask before moving anything if the count > 50.
3. **Move** — rerun without `--dry-run`.
4. **Verify** — report files moved, files skipped, and any unreadable files.

## Output

```
Moved 128 files into 11 folders (2023/03 … 2024/07).
Skipped 3 files: no EXIF and no readable mtime.
```

## Guardrails

- Dry-run first. Never move files whose date cannot be determined — list them instead.
- Do not delete originals; move only.

## Examples

**Input:** `~/Photos` with 131 unorganised JPEGs.
**Output:**

```
~/Photos/2023/03/IMG_0412.jpg
~/Photos/2023/04/IMG_0518.jpg
Moved 128 files into 11 folders.
Skipped 3 files: no EXIF and no readable mtime.
```

## Verification

- Folder names are always zero-padded two-digit months.
- A second run moves zero files (the operation is idempotent).
- Every skipped file is listed by name, never silently dropped.
*（内容由AI生成，仅供参考）*
