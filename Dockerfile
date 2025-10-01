# Imagen base de Python
FROM python:3.11-slim

# Carpeta de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Puerto que usará la app
EXPOSE 10000

# Comando de arranque
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
