@echo off
echo ==========================================
echo   PLANNER LOGISTICO MOTOS V2.0
echo   by Gilberto Thinkan
echo ==========================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor instala Python desde https://python.org
    pause
    exit /b 1
)

echo Python detectado correctamente.
echo.

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Iniciando servidor...
echo.
echo INSTRUCCIONES:
echo 1. El servidor se abrira en http://127.0.0.1:5000
echo 2. Usuario: admin
echo 3. Contraseña: 1234
echo 4. Presiona Ctrl+C para detener el servidor
echo.

python app.py

pause