# Portable Mode

SessionGuard supports a `--portable` flag that stores all data (database, uploads, etc.) in a `data/` folder next to the executable, instead of `%APPDATA%`.

## Usage

```bash
./SessionGuard.exe --portable
```

Or with the bundled app:
```
SessionGuard.exe --portable
```

## How it works

When `--portable` is passed:
1. Rust main() sets `SG_DATA_DIR=<executable_directory>/data`
2. Python backend reads `SG_DATA_DIR` and stores the SQLite DB and all uploads there
3. The `data/` folder is created automatically if it doesn't exist

## Data layout (portable)

```
SessionGuard.exe
data/
  config/
    sessionguard.db   ← SQLite database
  uploads/             ← uploaded videos/screenshots
  exports/             ← exported evidence packages
```

Without `--portable`, data goes to the usual `%APPDATA%\SessionGuard\config\` etc.