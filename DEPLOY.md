# Deployment Instructions

## ✅ Implementation Complete!

Everything is ready for deployment. The one-line installer now downloads both the app AND the conversation data automatically.

---

## 📦 What Was Built

Running `./scripts/build-release.sh` creates:

1. **soomgo_agent-0.1.0.tar.gz** (206KB) - The application
2. **data.tar.gz** (24MB) - 16K+ conversations + knowledge base

---

## 🚀 Deployment Steps

### Step 1: Create GitHub Repository

```bash
cd /Users/joonnam/Workspace/vf-data

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial release v0.1.0"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/soomgo-agent.git
git branch -M main
git push -u origin main
```

### Step 2: Build Release Packages

```bash
./scripts/build-release.sh
```

This creates:
- `dist/soomgo_agent-0.1.0.tar.gz`
- `dist/data.tar.gz`

### Step 3: Update install.sh with Your Repo

Edit `scripts/install.sh` **line 13**:

```bash
# Change this line:
GITHUB_REPO="USERNAME/soomgo-agent"

# To your actual repo:
GITHUB_REPO="yourusername/soomgo-agent"
```

Then commit and push:

```bash
git add scripts/install.sh
git commit -m "Update installer with repo URL"
git push
```

### Step 4: Create GitHub Release

1. Go to: `https://github.com/YOUR_USERNAME/soomgo-agent/releases/new`

2. Fill in:
   - **Tag**: `v0.1.0`
   - **Title**: `Soomgo Agent v0.1.0 - Beta`
   - **Description**:
     ```
     First beta release of Soomgo Agent.

     Includes:
     - TUI interface for browsing 16K+ conversations
     - AI agent with LangGraph
     - Knowledge base with FAQ and service info
     - First-run setup with API key configuration
     - Auto-update notifications
     ```

3. **Upload files** (drag and drop):
   - `dist/soomgo_agent-0.1.0.tar.gz`
   - `dist/data.tar.gz`

4. **Check**: "This is a pre-release" (for beta)

5. Click **"Publish release"**

### Step 5: Test Installation

Test the one-liner on a clean system (or new terminal session):

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/soomgo-agent/main/scripts/install.sh | sh
```

**What should happen:**
1. Installs uv (if needed)
2. Downloads app package (206KB) - fast
3. Installs soomgo command
4. Downloads data package (24MB) - takes 30-60 seconds
5. Extracts data to ~/.soomgo/data/
6. Shows success message

Then test:
```bash
soomgo
```

Should launch TUI with setup prompt for API key.

### Step 6: Share with Beta Users

Send in Slack:

```
🎉 Soomgo Agent is ready!

Install with one command:

curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/soomgo-agent/main/scripts/install.sh | sh

Then run: soomgo

Requirements:
- WezTerm (recommended): https://wezfurlong.org/wezterm/
- OpenAI API key (you'll be prompted on first run)

Note: Installation downloads ~24MB of conversation data.
```

---

## 📊 Package Details

### Application Package (206KB)
- Source code (agent, TUI, scraper, etc.)
- Dependencies list
- Scripts

### Data Package (24MB)
- 16,115 conversation files (`data/messages/`)
- Chat index (`chat_list_master.jsonl`)
- Knowledge base (`data/knowledge/`)
- Prompt templates (`data/prompts/`)

**Total download**: ~24.2MB
**Installed size**: ~300MB (with dependencies)

---

## 🔄 Updating Later

### To release v0.2.0:

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. **Build**:
   ```bash
   ./scripts/build-release.sh
   ```

3. **Create new GitHub release**: `v0.2.0`

4. **Upload new packages**

5. Users update with:
   ```bash
   # In TUI: Click "Update Now"
   # Or manually:
   uv tool upgrade soomgo-agent
   ```

---

## 🐛 Troubleshooting

### "Command not found: soomgo"

User needs to add to PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Data download fails

User can download manually:
```bash
curl -L https://github.com/YOUR_USERNAME/soomgo-agent/releases/download/v0.1.0/data.tar.gz | tar -xzf - -C ~/.soomgo/
```

### App works but no conversations

Data wasn't extracted. Run:
```bash
ls ~/.soomgo/data/messages/
```

If empty, redownload data (see above).

---

## 📝 Files Modified

- ✅ `scripts/install.sh` - Added data download steps
- ✅ `scripts/build-data.sh` - New script to build data package
- ✅ `scripts/build-release.sh` - Builds both packages
- ✅ `pyproject.toml` - Excludes unnecessary files
- ✅ `src/cli/tui.py` - Setup screen + update check
- ✅ `src/cli/config_manager.py` - Config management
- ✅ `INSTALL.md` - User installation guide

---

## ✨ What Users Experience

1. **Copy one command from Slack**
2. **Paste into WezTerm, press Enter**
3. **Wait 30-60 seconds** (downloads app + data)
4. **Run `soomgo`**
5. **Enter OpenAI API key**
6. **Start using the app immediately**

That's it! Single command, fully installed with all 16K+ conversations.

---

## 🎯 Next Steps After Beta

- [ ] Gather feedback
- [ ] Fix bugs
- [ ] Add features
- [ ] Publish to PyPI (optional, for easier install)
- [ ] Add custom domain: get.victoryformula.ai
- [ ] Create landing page
- [ ] Add analytics/telemetry
- [ ] Write comprehensive docs

---

**Ready to deploy!** Follow the 6 steps above and you're live. 🚀
