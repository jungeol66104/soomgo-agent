# Soomgo Agent Installation Guide

## Prerequisites

1. **Install WezTerm** (Recommended terminal)
   - Mac: Download from https://wezfurlong.org/wezterm/
   - Windows: Download from https://wezfurlong.org/wezterm/
   - Linux: Follow instructions at https://wezfurlong.org/wezterm/

2. **Open WezTerm**

## Installation

### One-Line Install

Run this command in WezTerm:

```bash
curl -fsSL https://raw.githubusercontent.com/USERNAME/soomgo-agent/main/scripts/install.sh | sh
```

**Note:** Replace `USERNAME/soomgo-agent` with your actual GitHub repository path.

The installer will:
1. Check and install `uv` package manager if needed
2. Download the Soomgo Agent package
3. Install the package and all dependencies
4. Set up the `soomgo` command

## First Run

After installation, launch the app:

```bash
soomgo
```

On first run, you'll see a setup screen:

```
┌────────────────────────────────┐
│     First-time Setup           │
│                                │
│  OpenAI API Key:               │
│  [sk-...]                      │
│                                │
│     [Save & Continue]          │
└────────────────────────────────┘
```

Enter your OpenAI API key and press the button to continue.

## Using the App

After setup, the main dashboard will appear:

```
Soomgo Agent

Run (coming soon)
Stop (coming soon)
Status (coming soon)

Chats

Enter: select  |  q: quit
```

### Available Features

- **Chats**: Browse 16,000+ real Soomgo conversations
- **Simulations**: Test the AI agent against historical conversations
- **Update Check**: Automatically notified when new versions are available

## Updating

When an update is available, you'll see it in the dashboard:

```
Update available: v0.2.0 - Update Now

[Select to update]
```

Or update manually:

```bash
uv tool upgrade soomgo-agent
```

## Troubleshooting

### Command not found: soomgo

If you see "command not found" after installation:

1. Add to your PATH in your shell config (`~/.zshrc` or `~/.bashrc`):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. Restart your terminal or run:
   ```bash
   source ~/.zshrc  # or ~/.bashrc
   ```

### Permission denied

If you get permission errors:

```bash
chmod +x ~/.local/bin/soomgo
```

### Update check fails

Update checks happen automatically but fail silently if:
- No internet connection
- GitHub API rate limit reached
- Network issues

The app will still work normally.

## Uninstalling

To remove Soomgo Agent:

```bash
uv tool uninstall soomgo-agent
rm -rf ~/.soomgo
```

## Support

For issues or questions, contact your Victory Formula team or check the GitHub repository.
