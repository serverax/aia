# SYNTHETIC ENTERPRISE - Python Dependencies Installation Script
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
Write-Host ""

$packages = @(
    "pytest==7.4.0",
    "qdrant-client==2.7.0",
    "sentence-transformers==2.2.2",
    "fastapi==0.104.0",
    "anthropic==0.7.0",
    "sqlalchemy==2.0.0",
    "pydantic==2.0.0",
    "redis==5.0.0",
    "psycopg2-binary==2.9.0",
    "opentelemetry-api==1.20.0",
    "opentelemetry-sdk==1.20.0",
    "opentelemetry-exporter-jaeger==1.20.0",
    "uvicorn==0.24.0",
    "requests==2.31.0",
    "pyyaml==6.0.1",
    "python-dotenv==1.0.0"
)

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q

Write-Host "Installing packages..." -ForegroundColor Yellow
foreach ($pkg in $packages) {
    Write-Host "  Installing: $pkg" -ForegroundColor Gray
    python -m pip install $pkg -q
}

Write-Host ""
Write-Host "✅ All dependencies installed!" -ForegroundColor Green
Write-Host ""
Write-Host "Verifying..." -ForegroundColor Cyan
python -m pytest --version
python -c "import qdrant_client; import fastapi; import anthropic; print('✅ Core packages verified')"
