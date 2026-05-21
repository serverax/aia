# 📥 HOW TO SET UP F:\aia\ - COMPLETE GUIDE

## STEP 1: DOWNLOAD THE BOOTSTRAP SCRIPT

1. Go to `/mnt/user-data/outputs/`
2. Download `bootstrap_windows.ps1`
3. Save it to `F:\` (your Windows drive root)

---

## STEP 2: RUN THE BOOTSTRAP SCRIPT

**Option A: Using PowerShell (Recommended)**

```powershell
# Open PowerShell as Administrator
# Navigate to F:\
cd F:\

# Allow script execution (one-time)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the bootstrap script
.\bootstrap_windows.ps1
```

**Option B: Manual Setup** (if script fails)

```powershell
mkdir F:\aia
cd F:\aia

# Create directories manually (see PROJECT_STRUCTURE.md for full list)
mkdir docs, sprints, apps, services, libs, infrastructure, tests, scripts, config, .github
mkdir .cursor

# Continue to Step 3
```

---

## STEP 3: DOWNLOAD ALL MARKDOWN FILES

Download these files from `/mnt/user-data/outputs/` and copy to `F:\aia\`:

### Foundation Files (Copy to F:\aia\ root)
- ✅ `00_START_HERE.md`
- ✅ `IMPLEMENTATION_SUMMARY.md`
- ✅ `README.md`
- ✅ `ARCHITECTURE.md`
- ✅ `AGENTS.md`
- ✅ `DEVELOPER_QUICK_START.md`
- ✅ `PROJECT_STRUCTURE.md`

### Documentation Files (Copy to F:\aia\docs\)
- ✅ `SECURITY_ARCHITECTURE.md`
- ✅ `REGULATORY_FRAMEWORK.md`

### Sprint Files (Copy to F:\aia\sprints\)
- ✅ `SPRINT_1_INFRASTRUCTURE.md`
- ✅ `SPRINT_2_ORCHESTRATION.md`
- ✅ `SPRINT_3_THROUGH_8.md`

### Cursor Configuration (Copy to F:\aia\.cursor\)
If bootstrap script created empty .cursor files, copy these:
- Check `.cursor\rules.md` - should have rules
- Check `.cursor\project_context.md` - should have context

---

## STEP 4: VERIFY THE STRUCTURE

Run this PowerShell command to verify:

```powershell
cd F:\aia

# Check key files exist
Test-Path ".\00_START_HERE.md"  # Should be True
Test-Path ".\README.md"  # Should be True
Test-Path ".\AGENTS.md"  # Should be True
Test-Path ".\.cursor\rules.md"  # Should be True
Test-Path ".\.cursorignore"  # Should be True
Test-Path ".\requirements.txt"  # Should be True

# Check key directories exist
Test-Path ".\docs\"  # Should be True
Test-Path ".\sprints\"  # Should be True
Test-Path ".\services\"  # Should be True
Test-Path ".\libs\"  # Should be True
Test-Path ".\infrastructure\"  # Should be True
Test-Path ".\.github\"  # Should be True

# List root directory
Get-ChildItem -Force
```

Expected output:
```
Mode  LastWriteTime     Length Name
----  ---------------  ------ ----
d----  5/20/2025         docs
d----  5/20/2025         sprints
d----  5/20/2025         services
d----  5/20/2025         libs
d----  5/20/2025         infrastructure
d----  5/20/2025         .cursor
d----  5/20/2025         .github
-a---  5/20/2025      12000     00_START_HERE.md
-a---  5/20/2025       8000     IMPLEMENTATION_SUMMARY.md
-a---  5/20/2025      15000     README.md
-a---  5/20/2025      20000     ARCHITECTURE.md
-a---  5/20/2025      18000     AGENTS.md
-a---  5/20/2025       7000     DEVELOPER_QUICK_START.md
-a---  5/20/2025       2000     requirements.txt
-a---  5/20/2025       1500     Makefile
-a---  5/20/2025        800     .cursorignore
-a---  5/20/2025       1200     .gitignore
```

---

## STEP 5: INITIALIZE GIT

```powershell
cd F:\aia

# Initialize Git repo
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial: Synthetic Enterprise project setup"

# (Optional) Connect to GitHub
# git remote add origin https://github.com/YOUR_ORG/synthetic-enterprise.git
# git branch -M main
# git push -u origin main
```

---

## STEP 6: SET UP DEVELOPMENT ENVIRONMENT

### Install Python Dependencies

```powershell
cd F:\aia

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import langgraph; print('✅ LangGraph installed')"
```

### Install Node.js Dependencies (for frontend)

```powershell
cd F:\aia\apps\web-dashboard

# Install Node packages
npm install

# Verify installation
npm list next
```

---

## STEP 7: OPEN IN CURSOR

1. Open Cursor editor
2. File → Open Folder
3. Select `F:\aia\`
4. Cursor will auto-detect `.cursor/rules.md` and `.cursor/project_context.md`
5. You should see Cursor's context menu includes your project rules

---

## STEP 8: START READING

1. Open `00_START_HERE.md`
2. Follow the reading order in that file
3. You'll be guided to the right documents for your role

---

## FOLDER STRUCTURE AT F:\aia\

After setup, your structure should look like:

```
F:\aia\
├── 00_START_HERE.md          ← Read this first
├── IMPLEMENTATION_SUMMARY.md
├── README.md
├── ARCHITECTURE.md
├── AGENTS.md
├── DEVELOPER_QUICK_START.md
├── PROJECT_STRUCTURE.md
├── requirements.txt
├── Makefile
├── .env.example
├── .gitignore
├── .cursorignore
│
├── .cursor/
│   ├── rules.md
│   ├── project_context.md
│   ├── agent_template.py
│   ├── cursor_commands.md
│   └── system_prompt
│
├── docs/
│   ├── SECURITY_ARCHITECTURE.md
│   ├── REGULATORY_FRAMEWORK.md
│   ├── DEPLOYMENT_GUIDE.md (to be created)
│   └── RUNBOOK.md (to be created)
│
├── sprints/
│   ├── SPRINT_1_INFRASTRUCTURE.md
│   ├── SPRINT_2_ORCHESTRATION.md
│   ├── SPRINT_3_THROUGH_8.md
│   └── SPRINT_TRACKING.md (optional)
│
├── services/
│   ├── orchestrator-agent/
│   ├── compliance-agent/
│   ├── analyst-agent/
│   └── editor-agent/
│
├── libs/
│   ├── communication/
│   ├── infrastructure/
│   ├── evaluation/
│   ├── tracing/
│   └── security/
│
├── apps/
│   ├── web-dashboard/
│   └── api-gateway/
│
├── infrastructure/
│   ├── terraform/
│   ├── helm-charts/
│   ├── talos-configs/
│   ├── sql/
│   ├── ci/
│   ├── templates/
│   ├── cosign/
│   └── tests/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
│
├── scripts/
├── config/
├── .github/
│   └── workflows/
│
└── .git/
```

---

## TROUBLESHOOTING

### PowerShell Script Execution Error

**Problem**: "PowerShell cannot execute scripts"

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Git Not Found

**Problem**: "git is not recognized"

**Solution**: Install Git for Windows: https://git-scm.com/download/win

### Python Not in PATH

**Problem**: "python is not recognized"

**Solution**: 
- Reinstall Python and check "Add Python to PATH"
- Or use full path: `C:\Python311\python.exe -m venv venv`

### Permission Denied

**Problem**: "Access is denied"

**Solution**: Run PowerShell as Administrator

### .cursor Files Empty

**Problem**: Files were created but are empty

**Solution**: Copy the content from the `.cursor/` section above into each file

---

## NEXT IMMEDIATE ACTIONS

### 1. Get Familiar (30 minutes)
```powershell
cd F:\aia
code 00_START_HERE.md  # Open in VS Code or Cursor
```

### 2. Share with Team (if applicable)
```
Email to team:
Subject: Synthetic Enterprise Project Structure Ready

Hi team,

The complete project documentation and structure are set up at F:\aia\

Please:
1. Clone the repo
2. Read 00_START_HERE.md
3. Open F:\aia\ in Cursor
4. Follow your role-specific path (see DEVELOPER_QUICK_START.md)

Let's kickoff Sprint 1!
```

### 3. Start Sprint 1 (if ready)
- Open `sprints/SPRINT_1_INFRASTRUCTURE.md`
- Follow Task 1.1 (Provision infrastructure)
- Assign roles to team members

---

## FILE SIZES (Download Estimate)

All markdown files total: ~2 MB  
Bootstrap script: ~50 KB  

**Total to download: ~2.1 MB** (can be zipped into one file)

---

## CHECKLIST: Project Ready ✅

- [ ] F:\aia\ directory created
- [ ] Bootstrap script run (or manual setup complete)
- [ ] All markdown files downloaded and in place
- [ ] Git initialized
- [ ] Python dependencies installed
- [ ] Node dependencies installed (for frontend)
- [ ] Cursor opened with F:\aia\
- [ ] 00_START_HERE.md read
- [ ] README.md read
- [ ] AGENTS.md read (your agent's section)
- [ ] Your sprint document identified (SPRINT_1, SPRINT_2, or SPRINT_3_THROUGH_8)
- [ ] Ready to code!

---

## SUPPORT

If you get stuck:

1. **Architecture questions** → Read ARCHITECTURE.md
2. **Agent questions** → Read AGENTS.md
3. **Sprint tasks** → Read your sprint document
4. **Security questions** → Read SECURITY_ARCHITECTURE.md
5. **Compliance questions** → Read REGULATORY_FRAMEWORK.md

All answers are in the documentation. 📚

---

**You're ready. Let's build Synthetic Enterprise!** 🚀

