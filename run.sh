#!/bin/bash

echo "=========================================="
echo "  PLANNER LOGISTICO MOTOS V2.0"
echo "  by Gilberto Thinkan"
echo "=========================================="
echo ""

echo "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no está instalado"
    echo "Por favor instala Python3"
    exit 1
fi

echo "Python detectado correctamente."
echo ""

echo "Instalando dependencias..."
pip3 install -r requirements.txt

echo ""
echo "Iniciando servidor..."
echo ""
echo "INSTRUCCIONES:"
echo "1. El servidor se abrirá en http://127.0.0.1:5000"
echo "2. Usuario: admin"
echo "3. Contraseña: 1234"
echo "4. Presiona Ctrl+C para detener el servidor"
echo ""

python3 app.py