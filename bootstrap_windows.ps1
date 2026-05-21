#!/usr/bin/env pwsh
# bootstrap_windows.ps1
# Run this script in F:\aia\ to set up the entire project structure

Write-Host "🚀 Synthetic Enterprise - Windows Bootstrap Script" -ForegroundColor Cyan
Write-Host "This script will set up the complete project structure in F:\aia\" -ForegroundColor Yellow
Write-Host ""

# Check if running as admin (recommended)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')
if (-not $isAdmin) {
    Write-Host "⚠️  Recommended to run as Administrator" -ForegroundColor Yellow
}

# Create root directory if it doesn't exist
$rootPath = "F:\aia"
if (-not (Test-Path $rootPath)) {
    Write-Host "Creating root directory: $rootPath" -ForegroundColor Green
    New-Item -ItemType Directory -Path $rootPath -Force | Out-Null
}

Set-Location $rootPath
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# Function to create directory
function CreateDir {
    param([string]$path)
    if (-not (Test-Path $path)) {
        Write-Host "Creating: $path" -ForegroundColor DarkGray
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# Function to create file
function CreateFile {
    param([string]$path, [string]$content)
    if (-not (Test-Path $path)) {
        Write-Host "Creating: $path" -ForegroundColor DarkGray
        New-Item -ItemType File -Path $path -Force | Out-Null
        if ($content) {
            Set-Content -Path $path -Value $content
        }
    }
}

Write-Host "📁 Creating directory structure..." -ForegroundColor Cyan

# Create main directories
CreateDir ".\docs"
CreateDir ".\sprints"
CreateDir ".\apps\web-dashboard"
CreateDir ".\apps\api-gateway"
CreateDir ".\services\orchestrator-agent\tests"
CreateDir ".\services\compliance-agent\tests"
CreateDir ".\services\analyst-agent\tests"
CreateDir ".\services\editor-agent\tests"
CreateDir ".\libs\communication"
CreateDir ".\libs\infrastructure"
CreateDir ".\libs\evaluation"
CreateDir ".\libs\tracing"
CreateDir ".\libs\security"
CreateDir ".\infrastructure\terraform"
CreateDir ".\infrastructure\helm-charts\echo-agent"
CreateDir ".\infrastructure\helm-charts\orchestrator-agent"
CreateDir ".\infrastructure\helm-charts\compliance-agent"
CreateDir ".\infrastructure\helm-charts\analyst-agent"
CreateDir ".\infrastructure\helm-charts\editor-agent"
CreateDir ".\infrastructure\talos-configs"
CreateDir ".\infrastructure\sql"
CreateDir ".\infrastructure\ci"
CreateDir ".\infrastructure\templates"
CreateDir ".\infrastructure\cosign"
CreateDir ".\infrastructure\tests"
CreateDir ".\tests\unit"
CreateDir ".\tests\integration"
CreateDir ".\tests\evals"
CreateDir ".\scripts"
CreateDir ".\.github\workflows"
CreateDir ".\config"
CreateDir ".\.cursor"

Write-Host "✅ Directory structure created" -ForegroundColor Green
Write-Host ""

Write-Host "📄 Creating .cursor files..." -ForegroundColor Cyan

# Create .cursor/rules.md
$cursorRules = @"
# Cursor Rules for Synthetic Enterprise

You are assisting in building a multi-agent AI orchestration system for UK professional services.

## INVIOLABLE CONSTRAINTS

### Architecture Constraints
- **NEVER create monolithic services.** Services must communicate via Redis message bus only.
- **NEVER call agent functions directly.** All communication is async via Redis Streams/Pub/Sub.
- **Infrastructure and Orchestration are separate layers.** Don't mix K3s manifests with agent logic.

### Agent Behavior Constraints (See AGENTS.md)
- **Orchestrator**: Decomposes tasks; routes to agents; does NOT do heavy reasoning
- **Compliance Officer**: Has VETO power; can block outputs; MUST cite all decisions
- **Analyst**: MUST cite all sources; no hallucination; honest confidence scores
- **Editor**: Formats only; does NOT rewrite content or change meaning

### LLM & Determinism Constraints
- **ALWAYS set temperature=0** for all LLM calls (determinism required for audit)
- **NEVER use random or non-deterministic operations** in agent critical paths
- **NEVER fine-tune models.** Use Claude Sonnet 4 via Anthropic API only.
- **EVERY output must include citations.** If you can't cite it, it fails review.

### Data & Security Constraints
- **NEVER allow cross-client data access.** K3s namespaces + Milvus partitions enforce isolation.
- **NEVER store plaintext secrets.** Use K3s Sealed Secrets or similar.
- **ALL agent code must be Wasm-compatible.** Nothing that requires native syscalls.
- **NEVER bypass the Compliance Officer veto.** If Compliance rejects something, it stays rejected until revised.

## RED FLAGS (Stop & Ask First)

🚫 Adding randomness to agent logic  
🚫 Direct function calls between agents  
🚫 Plaintext secrets in code  
🚫 Agent making autonomous high-stakes decisions  
🚫 Cross-tenant data access  
🚫 Bypassing Compliance Officer veto  
🚫 Temperature > 0 for critical agents  
🚫 Outputs without citations  

When you see these, STOP and ask the architect.

---

**Golden Rule**: This system is only as good as its constraints. Every rule exists for a reason.
"@

CreateFile ".\.cursor\rules.md" $cursorRules

# Create .cursor/project_context.md
$projectContext = @"
# Synthetic Enterprise: Project Context for Cursor

## System Architecture (TL;DR)
User Request → Orchestrator → Decomposes → Routes to Agents → Compliance Reviews → Editor Formats → Output

## The 4 Agents
1. **Orchestrator** (Manager): Decompose & route. DON'T do reasoning.
2. **Compliance Officer** (Gatekeeper): Verify UK law. Has VETO power.
3. **Domain Analyst** (Researcher): Research & analyze. MUST cite everything.
4. **Editor** (Polish): Format only. DON'T rewrite content.

## Tech Stack
- Language: Python 3.11
- Orchestration: LangGraph
- Message Broker: Redis (Streams + Pub/Sub)
- Vector DB: Qdrant (Compliance), Milvus (Analyst)
- LLM: Claude Sonnet 4 (temperature=0 always)
- Infrastructure: Talos Linux + K3s
- Security: WasmEdge + Cosign

## Key Constraints
- **Determinism**: temperature=0, no randomness in critical paths
- **Event-Driven**: All agent communication via Redis (async)
- **Auditability**: Every decision logged with reasoning
- **Compliance**: UK GDPR/SRA baked in
- **Human Control**: Humans make final high-stakes decisions

## Reference Documents
- AGENTS.md - Agent operating principles
- ARCHITECTURE.md - System design
- SECURITY_ARCHITECTURE.md - Threat model & controls
- REGULATORY_FRAMEWORK.md - UK compliance
- SPRINT_*.md - Sprint-specific tasks
"@

CreateFile ".\.cursor\project_context.md" $projectContext

# Create .cursorignore
$cursorIgnore = @"
.git/
node_modules/
__pycache__/
.venv/
venv/
*.pyc
.DS_Store
.env
.env.local
secrets/
keys/
*.key
*.pem
*.p12
infrastructure/terraform/.terraform/
infrastructure/terraform/terraform.tfvars
docs/DECISION_RECORDS.md
docs/DEPLOYMENT_GUIDE.md
docs/RUNBOOK.md
"@

CreateFile ".\.cursorignore" $cursorIgnore

# Create .gitignore
$gitIgnore = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*.swn
*~

# Environment
.env
.env.local
.env.*.local

# Secrets
*.key
*.pem
*.p12
cosign.key
infrastructure/cosign/cosign.key

# Terraform
infrastructure/terraform/.terraform/
infrastructure/terraform/terraform.tfvars
*.tfstate
*.tfstate.*

# Node
node_modules/
dist/
build/

# OS
.DS_Store
Thumbs.db

# Misc
.cache/
*.log
"@

CreateFile ".\.gitignore" $gitIgnore

Write-Host "✅ .cursor files created" -ForegroundColor Green
Write-Host ""

# Create basic Python files
Write-Host "📝 Creating Python files..." -ForegroundColor Cyan

CreateFile ".\libs\__init__.py" ""
CreateFile ".\libs\communication\__init__.py" ""
CreateFile ".\libs\infrastructure\__init__.py" ""
CreateFile ".\libs\evaluation\__init__.py" ""
CreateFile ".\libs\tracing\__init__.py" ""
CreateFile ".\libs\security\__init__.py" ""
CreateFile ".\tests\__init__.py" ""
CreateFile ".\tests\unit\__init__.py" ""
CreateFile ".\tests\integration\__init__.py" ""
CreateFile ".\tests\evals\__init__.py" ""

Write-Host "✅ Python files created" -ForegroundColor Green
Write-Host ""

# Create requirements.txt
Write-Host "📋 Creating requirements.txt..." -ForegroundColor Cyan

$requirements = @"
# Core
langgraph==0.1.0
langchain==0.1.0
langchain-anthropic==0.1.0
pydantic==2.5.0

# Data & Databases
redis==5.0.0
psycopg2-binary==2.9.9
qdrant-client==2.7.0
pymilvus==2.3.0

# Web
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0

# Observability
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-jaeger==1.21.0
prometheus-client==0.19.0

# Security
pyjwt==2.8.1
cryptography==41.0.7

# Testing
pytest==7.4.3
pytest-asyncio==0.23.1
pytest-cov==4.1.0

# Utilities
python-dotenv==1.0.0
httpx==0.25.2
python-dateutil==2.8.2
"@

CreateFile ".\requirements.txt" $requirements

Write-Host "✅ requirements.txt created" -ForegroundColor Green
Write-Host ""

# Create package.json template
Write-Host "📦 Creating package.json for frontend..." -ForegroundColor Cyan

$packageJson = @"
{
  "name": "synthetic-enterprise-dashboard",
  "version": "1.0.0",
  "description": "Real-time dashboard for Synthetic Enterprise agent orchestration",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-use-websocket": "^4.7.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
"@

CreateFile ".\apps\web-dashboard\package.json" $packageJson

Write-Host "✅ package.json created" -ForegroundColor Green
Write-Host ""

# Create Makefile
Write-Host "📋 Creating Makefile..." -ForegroundColor Cyan

$makefile = @"
.PHONY: help install test lint clean

help:
	@echo "Synthetic Enterprise - Available commands:"
	@echo "  make install       - Install all dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run linters"
	@echo "  make clean         - Clean up generated files"
	@echo "  make bootstrap     - Bootstrap the project"

install:
	pip install -r requirements.txt
	cd apps/web-dashboard && npm install

test:
	pytest tests/ -v --cov=libs --cov=services

lint:
	black libs/ services/ tests/
	isort libs/ services/ tests/
	flake8 libs/ services/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

bootstrap:
	@echo "Setting up Synthetic Enterprise..."
	@echo "1. Install dependencies"
	make install
	@echo "2. Create .env file"
	cp .env.example .env
	@echo "✅ Project bootstrapped! Read 00_START_HERE.md to begin."
"@

CreateFile ".\Makefile" $makefile

Write-Host "✅ Makefile created" -ForegroundColor Green
Write-Host ""

# Create .env.example
Write-Host "⚙️  Creating .env.example..." -ForegroundColor Cyan

$envExample = @"
# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=synthetic_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=synthetic_enterprise

# Qdrant (Compliance Officer)
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Milvus (Domain Analyst)
MILVUS_HOST=milvus
MILVUS_PORT=19530

# Jaeger (Tracing)
JAEGER_HOST=jaeger
JAEGER_PORT=6831

# Environment
ENVIRONMENT=development
DEBUG=true
"@

CreateFile ".\.env.example" $envExample

Write-Host "✅ .env.example created" -ForegroundColor Green
Write-Host ""

# Create README files for each service
Write-Host "📖 Creating service README files..." -ForegroundColor Cyan

$orchestratorReadme = @"
# Orchestrator Agent

Central coordinator for task decomposition and routing.

## Quick Start

```bash
cd services/orchestrator-agent
pip install -r requirements.txt
python main.py
```

## Architecture

- **Intent Parser**: Parses user requests into structured tasks
- **Task Decomposer**: Breaks complex goals into atomic subtasks
- **Router**: Routes tasks to appropriate specialist agents
- **Conflict Resolver**: Handles disagreements between agents

## Files

- `main.py` - Agent entry point
- `state.py` - State machine definitions
- `nodes.py` - LangGraph nodes (intent parser, decomposer)
- `graph.py` - LangGraph workflow
- `router.py` - Task routing logic
- `conflict_resolver.py` - Conflict resolution protocol

## Testing

```bash
pytest tests/ -v
```

See SPRINT_2_ORCHESTRATION.md for detailed specifications.
"@

CreateFile ".\services\orchestrator-agent\README.md" $orchestratorReadme

Write-Host "✅ Service README files created" -ForegroundColor Green
Write-Host ""

Write-Host "🎉 Project structure created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Download .md files from /mnt/user-data/outputs/ to F:\aia\" -ForegroundColor White
Write-Host "  2. Copy the following files:" -ForegroundColor White
Write-Host "     - 00_START_HERE.md" -ForegroundColor DarkGray
Write-Host "     - IMPLEMENTATION_SUMMARY.md" -ForegroundColor DarkGray
Write-Host "     - README.md" -ForegroundColor DarkGray
Write-Host "     - ARCHITECTURE.md" -ForegroundColor DarkGray
Write-Host "     - AGENTS.md" -ForegroundColor DarkGray
Write-Host "     - DEVELOPER_QUICK_START.md" -ForegroundColor DarkGray
Write-Host "     - docs/* (all files)" -ForegroundColor DarkGray
Write-Host "     - sprints/* (all files)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Initialize Git:" -ForegroundColor White
Write-Host "     cd F:\aia" -ForegroundColor DarkGray
Write-Host "     git init" -ForegroundColor DarkGray
Write-Host "     git add ." -ForegroundColor DarkGray
Write-Host "     git commit -m 'Initial: Synthetic Enterprise project setup'" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  4. Read 00_START_HERE.md to begin!" -ForegroundColor Green
Write-Host ""
"@

# Run bootstrap function
CreateFile ".\bootstrap_windows.ps1" ""

Write-Host "✅ Bootstrap script ready in: $rootPath\bootstrap_windows.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Project structure complete! F:\aia\ is ready for development." -ForegroundColor Green
