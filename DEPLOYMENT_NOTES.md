# Deployment Notes

## Implementation Complete

All deployment infrastructure has been implemented:

### ✅ Completed

1. **pyproject.toml** - Updated with all dependencies (textual, pyyaml, requests, packaging)
2. **build-release.sh** - Build script creates distributable package
3. **install.sh** - One-line installer for users
4. **config_manager.py** - Configuration management (load/save API keys)
5. **SetupScreen** - First-run setup modal in TUI (prompts for API key)
6. **Update check** - Dashboard checks GitHub for new versions
7. **INSTALL.md** - User installation guide

### 📦 Package Build

Current package: **92KB** (without conversation data)

Build command:
```bash
./scripts/build-release.sh
```

Output: `dist/soomgo_agent-0.1.0.tar.gz`

### ⚠️ Important: Conversation Data

The 16K conversations (285K+ messages, ~100-200MB) are **NOT included** in the package.

**Options for handling data:**

#### Option A: Manual data copy (for beta)
Users copy data manually after install:
```bash
# After installation
cp -r /path/to/dev/data ~/.soomgo/
```

#### Option B: Separate data package
Create separate downloadable data package:
```bash
# After soomgo install
soomgo download-data  # Downloads conversations separately
```

#### Option C: Include minimal data
Include just prompts and knowledge base (~1MB), skip conversation history

#### Option D: Git LFS (for GitHub)
Use Git Large File Storage for conversation data in repo

**Recommendation for beta**: Use **Option A** (manual copy) since users will have access to the dev environment.

### 🚀 Deployment Steps

#### Step 1: Prepare Repository

1. Create GitHub repository (private for beta)
2. Push code:
   ```bash
   git init
   git add .
   git commit -m "Initial deployment setup"
   git remote add origin https://github.com/USERNAME/soomgo-agent.git
   git push -u origin main
   ```

#### Step 2: Build and Create Release

1. Build package:
   ```bash
   ./scripts/build-release.sh
   ```

2. Create GitHub Release:
   - Go to: https://github.com/USERNAME/soomgo-agent/releases/new
   - Tag version: `v0.1.0`
   - Release title: `Soomgo Agent v0.1.0 - Beta`
   - Upload: `dist/soomgo_agent-0.1.0.tar.gz`

#### Step 3: Update install.sh

Edit `scripts/install.sh` and replace:
- `USERNAME/soomgo-agent` with your actual GitHub repo path
- Line 13-14: Update GITHUB_REPO variable

#### Step 4: Test Installation

Test the one-liner:
```bash
curl -fsSL https://raw.githubusercontent.com/USERNAME/soomgo-agent/main/scripts/install.sh | sh
```

#### Step 5: Share with Users (Slack)

Share in Slack:
```
Install Soomgo Agent:

curl -fsSL https://raw.githubusercontent.com/USERNAME/soomgo-agent/main/scripts/install.sh | sh

After installation:
1. Run: soomgo
2. Enter your OpenAI API key when prompted
3. Start using the app!

Note: If you need conversation data, copy it manually:
cp -r /path/to/vf-data/data ~/.soomgo/
```

### 🔧 Configuration

Users will be prompted for:
- OpenAI API key (required on first run)

Config stored in: `~/.soomgo/config/config.yaml`

### 🔄 Updates

When new version is released:
- Users see update notification in dashboard
- Click "Update Now" or run: `uv tool upgrade soomgo-agent`

### 🐛 Troubleshooting

Common issues documented in INSTALL.md:
- Command not found → Add to PATH
- Permission denied → chmod +x
- Update check fails → Silently handled

### 📝 TODOs for Production

Before public launch:

1. **Update install.sh** with real GitHub repo URL
2. **Decide on conversation data distribution** (Options A-D above)
3. **Add analytics/telemetry** (optional)
4. **Create landing page** at victoryformula.ai
5. **Set up custom domain redirect**: get.victoryformula.ai → GitHub install script
6. **Publish to PyPI** (optional, for easier install)
7. **Add version metadata** (replace hardcoded "0.1.0" with dynamic version)
8. **Add error reporting** (Sentry, LogRocket, etc.)
9. **Create demo video** or screenshots
10. **Write comprehensive documentation**

### 🎯 Beta Testing Checklist

- [ ] Create private GitHub repo
- [ ] Build package and create v0.1.0 release
- [ ] Update install.sh with real repo URL
- [ ] Test installation on clean Mac
- [ ] Test installation on clean Windows (if supporting)
- [ ] Test first-run setup flow
- [ ] Test update mechanism
- [ ] Share in Slack with beta users
- [ ] Gather feedback
- [ ] Iterate and improve

### 📞 Support

For questions or issues during deployment:
- Check INSTALL.md for user-facing docs
- Check this file for deployment details
- Review code comments in key files:
  - `src/cli/main.py` - Entry points
  - `src/cli/tui.py` - TUI and setup screen
  - `src/cli/config_manager.py` - Configuration
