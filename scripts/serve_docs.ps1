# PowerShell script to launch a local hot-reloading MkDocs documentation server
Write-Host "Checking for MkDocs installation..." -ForegroundColor Cyan
if (-not (Get-Command mkdocs -ErrorAction SilentlyContinue)) {
    Write-Host "MkDocs not found. Installing mkdocs and mkdocs-material..." -ForegroundColor Yellow
    pip install mkdocs mkdocs-material
}

Write-Host "Starting MkDocs server at http://127.0.0.1:8000 ..." -ForegroundColor Green
mkdocs serve -a 127.0.0.1:8000
