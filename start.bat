@echo off
start "Backend" powershell -NoExit -Command "Set-Location -LiteralPath '%~dp0'; uvicorn app.main:app --reload"
start "Frontend" powershell -NoExit -Command "Set-Location -LiteralPath '%~dp0frontend'; npm run dev"