Cypher Spectre DeepSight - Luau Runtime Deobfuscator

Bot de Discord diseñado para analizar, reconstruir y deofuscar scripts Lua/Luau mediante ejecución controlada en sandbox y análisis heurístico avanzado.

---

⚡ Características

- Deobfuscación Avanzada
  Detecta y reconstruye múltiples patrones comunes de ofuscación en Lua y Luau.

- Análisis de Seguridad Integrado
  Escaneo automático antes y después del dump para detectar comportamiento malicioso.

- Multi-deployment
  Compatible con Railway, Docker y ejecución local.

- Límites de Seguridad
  Timeouts, límites de tamaño y protección contra loops o dumps infinitos.

- Sandbox Controlado
  Ejecución segura de scripts Lua para reconstrucción dinámica.

---

📦 Requisitos

- Python 3.10+
- Lua 5.1+ o LuaJIT
- Token de Discord Bot

---

🔧 Instalación Local

Linux / macOS

# 1. Clonar el repositorio
git clone https://github.com/tuusuario/cypher-spectre.git
cd cypher-spectre

# 2. Ejecutar setup
chmod +x setup.sh
./setup.sh

# 3. Configurar variables
cp .env.example .env
# editar .env y agregar DISCORD_TOKEN

---

Windows

# 1. Clonar repositorio
git clone https://github.com/tuusuario/cypher-spectre.git
cd cypher-spectre

# 2. Instalar Lua
# descargar desde lua.org

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Variables de entorno
copy .env.example .env

---

🐳 Deployment con Docker

# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f

---

☁️ Deployment en Railway

Opción 1 — Desde GitHub

1. Haz fork del repositorio
2. Ve a railway.app
3. Crear nuevo proyecto
4. Conectar repositorio
5. Agregar variable:

DISCORD_TOKEN=tu_token

6. Deploy automático ✔

---

Opción 2 — Railway CLI

npm install -g @railway/cli

railway login
railway init

railway variables set DISCORD_TOKEN=tu_token

railway up

---

🧠 Uso del Bot

Cuando el bot esté online:

.spectre [archivo | url]

Ejemplos

.spectre (archivo adjunto .lua)
.spectre https://example.com/script.lua
.spectre https://pastebin.com/raw/abc123

---

📂 Tipos de Archivo

Aceptados:

- ".lua"
- ".luau"
- ".txt"

---

📏 Límites

Tipo| Límite
Tamaño máximo| 8 MB
Timeout| 30 s
Output máximo| 8 MB

---

🔐 Sistema de Seguridad

Cypher Spectre escanea automáticamente:

- acceso a sistema ("debug.getinfo")
- ejecución shell ("os.execute")
- lectura de archivos sensibles
- exfiltración de variables
- ofuscación pesada

Los scripts peligrosos son bloqueados automáticamente.

---

🧩 Estructura del Proyecto

cypher-spectre/
│
├─ bot.py
├─ scanner.py
├─ spectre_dumper.lua
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ Procfile
├─ railway.toml
├─ setup.sh
├─ .env.example
│
└─ tests/
   ├─ test_bot.py
   └─ test_scanner.py

---

🧪 Testing

python -m pytest tests/

Coverage:

python -m pytest --cov=. tests/

---

⚙️ Configuración Avanzada

Variables de Entorno

DISCORD_TOKEN=tu_token
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=8

---

Configuración del Engine

Archivo:

spectre_dumper.lua

local CONFIG = {

    MAX_DEPTH = 16,
    MAX_TABLE_ITEMS = 200,
    MAX_OUTPUT_SIZE = 8 * 1024 * 1024,
    TIMEOUT_SECONDS = 8.0,
    TRACE_CALLS = true

}

---

🤝 Contribuciones

1. Fork
2. Crear rama
3. Commit
4. Push
5. Pull Request

---

📜 Changelog

v2.0.0

- engine Luau reconstruido
- sistema de seguridad mejorado
- soporte Docker completo
- optimización Railway
- refactor completo del código

---

📄 Licencia

MIT License.

---

⚠️ Disclaimer

Cypher Spectre está diseñado para investigación, análisis y aprendizaje.
Utiliza esta herramienta de forma responsable.

---

💬 Soporte

Si encuentras un problema:

1. revisa Issues
2. abre un Issue nuevo
3. incluye logs y entorno

---

⭐ Si el proyecto te fue útil, considera darle una estrella en GitHub.