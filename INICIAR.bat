@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Falta configurar el entorno del proyecto.
 echo Ejecuta powershell -ExecutionPolicy Bypass -File CONFIGURAR.ps1
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -X utf8 main.py
if errorlevel 1 (
 echo No se pudo iniciar. Ejecuta CONFIGURAR.ps1 y revisa el mensaje de error.
 pause
)
