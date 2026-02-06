# =============================================================================
# Plataforma de Transparencia Presupuestaria - CUCEA
# Imagen para desarrollo y despliegue. Todo el equipo usa el mismo entorno.
# Uso: docker-compose up --build
# =============================================================================

FROM python:3.11-slim

# Evitar prompts de apt y crear directorio de la app
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Dependencias del sistema (si se necesitan más adelante)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación
COPY . .

# Puerto Flask por defecto
EXPOSE 5000

# Crear directorio instance para SQLite (permisos)
RUN mkdir -p instance

# Arranque: ejecutar la app (sobrescribir con docker-compose si se usa otro comando)
CMD ["python", "app.py"]
