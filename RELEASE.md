# Release Process

This document describes the complete process for releasing a new version of Soomgo Agent.

## Prerequisites

- All changes committed and pushed to `main` branch
- Version number decided (keep at `0.1.0` unless bumping)

## 1. Build Release Packages

Run the build script to create both distribution packages:

```bash
./scripts/build-release.sh
```

This creates two files in `dist/`:
- `soomgo_agent-0.1.0.tar.gz` (~209 KB) - Application package
- `data.tar.gz` (~24 MB) - Conversation data

## 2. Create GitHub Release

1. Go to: https://github.com/jungeol66104/soomgo-agent/releases/new
2. Create new tag: `v0.1.0`
3. Release title: `v0.1.0`
4. Release notes (example):

```markdown
## Improvements
- **Production-ready TUI**: Setup and settings screens with proper placeholders and password masking
- **Better UX**: Fixed input focus issue - keyboard shortcuts work when not typing
- **Cleaner menu**: Reorganized dashboard with Chats → Settings → Logs structure

## Bug Fixes
- Removed dev-only `soomgo-dev` command from production install
```

5. Upload both files:
   - `dist/soomgo_agent-0.1.0.tar.gz`
   - `dist/data.tar.gz`

6. Publish release

## 3. Installation Commands

### Uninstall existing version

```bash
uv tool uninstall soomgo-agent
```

### Install from GitHub Release (production)

#### macOS / Linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/jungeol66104/soomgo-agent/main/scripts/install.sh | sh
```

#### Windows (PowerShell / WezTerm)

```powershell
powershell -c "irm https://raw.githubusercontent.com/jungeol66104/soomgo-agent/main/scripts/install.ps1 | iex"
```

Both one-line commands will:
- Check/install `uv` package manager if needed
- Download the application package from the release
- Install it with `uv tool install`
- Download and extract conversation data to `~/.soomgo/data` (or `%USERPROFILE%\.soomgo\` on Windows)
- Verify the installation

### Install from local dist (testing)

```bash
uv tool install dist/soomgo_agent-0.1.0.tar.gz
```

### Verify installation

```bash
soomgo --version
```

## 4. Development Setup

For development work, the local `soomgo-dev` command should be used:

```bash
# Create symlink (one-time setup)
ln -sf /Users/joonnam/Workspace/vf-data/soomgo-dev /Users/joonnam/.local/bin/soomgo-dev

# Run development version
soomgo-dev

# Or run directly
./soomgo-dev
```

The development version:
- Runs local source code (not installed package)
- Uses `dev` environment (stores data in project directory)
- Reflects code changes immediately

## 5. Post-Release

After publishing the release:

1. Test the installation on a clean system (or after uninstall)
2. Verify the TUI launches correctly
3. Check that conversation data loaded properly
4. Share the install command with users

## Notes

- Production install uses `soomgo` command only (no `soomgo-dev`)
- Development uses `soomgo-dev` command (local script)
- Version should stay at `0.1.0` unless explicitly bumping
- The `scripts/build-release.sh` script automatically reads version from `pyproject.toml`
