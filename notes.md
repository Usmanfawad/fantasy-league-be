# Boilerplate cheatsheet
Project notes moved into README. Consider removing this file if not needed.
## RUFF!! https://docs.astral.sh/ruff/

## Ruff lint and formatting

```
ruff check   # Lint all files in the current directory.
ruff format  # Format all files in the current directory.
```

## Dev server
```
uvicorn main:app --reload
```

## ruff check
ruff check is the primary entrypoint to the Ruff linter. It accepts a list of files or directories, and lints all discovered Python files, optionally fixing any fixable errors. When linting a directory, Ruff searches for Python files recursively in that directory and all its subdirectories:

```
ruff check                  # Lint files in the current directory.
ruff check --fix            # Lint files in the current directory and fix any fixable errors.
ruff check --watch          # Lint files in the current directory and re-lint on change.
ruff check path/to/code/    # Lint files in `path/to/code`.
```
For the full list of supported options, run ruff check --help.

## ruff format

ruff format is the primary entrypoint to the formatter. It accepts a list of files or directories, and formats all discovered Python files:

```
ruff format                   # Format all files in the current directory.
ruff format path/to/code/     # Format all files in `path/to/code` (and any subdirectories).
ruff format path/to/file.py   # Format a single file.
```

Similar to Black, running ruff format /path/to/file.py will format the given file or directory in-place, while ruff format --check /path/to/file.py will avoid writing any formatted files back, and instead exit with a non-zero status code upon detecting any unformatted files.

For the full list of supported options, run ruff format --help.