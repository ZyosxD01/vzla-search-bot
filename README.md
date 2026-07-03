# 🇻🇪 Búsqueda Terremoto Venezuela — Bot Federado

Búsqueda agregada de personas desaparecidas tras el terremoto del 24 de junio de 2026.
Consulta en vivo 4 plataformas (Tier 1 + Cruz Roja/ICRC), formatea la respuesta con
IA en español e inglés, y la presenta como un chat web sin registro ni instalación.

**Arquitectura:** Frontend estático + Backend FastAPI con Playwright + IA MiniMax.
**Hosting:** Render.com (free tier).
**URL ejemplo:** `https://vzla-search-bot.onrender.com`

---

## ⚙️ Lo que hace

1. Recibe un nombre (o fragmento) en el chat
2. Detecta idioma (ES / EN)
3. Consulta en paralelo 4 plataformas con Playwright:
   - desaparecidosterremotovenezuela.com (26k+ reportes)
   - venezuelatebusca.com (10k+ reportes)
   - statusvzla.com (Búsqueda Cruzada)
   - Cruz Roja / ICRC Restoring Family Links
4. Consolida resultados
5. MiniMax API formatea la respuesta humanitariamente en ES + EN
6. Devuelve respuesta con links a las fuentes originales

**Sin base de datos propia.** Todo es consulta en vivo. Sin fotos almacenadas. Sin datos
personales persistidos. Cero exposición UCPA.

---

## 🚀 Deploy paso a paso en Render

### 1. Sube el código a GitHub

```powershell
cd C:\Users\ZyosxD\.openclaw\workspace\venezuela-search-bot
git init
git add .
git commit -m "Initial bot"
# Crea un repo nuevo en github.com (vacío, sin README ni .gitignore)
# luego conecta:
git remote add origin https://github.com/TU_USUARIO/vzla-search-bot.git
git branch -M main
git push -u origin main
```

### 2. Crea el servicio en Render

1. Entra a https://dashboard.render.com
2. Click **New +** → **Blueprint**
3. Conecta tu repo de GitHub
4. Render detecta automáticamente `render.yaml`
5. Click **Apply** → Render empieza a construir

> La primera build tarda ~5-8 minutos (instala Chromium y deps).
> Si algo falla, abre la pestaña "Logs" para ver el error.

### 3. Configura tu API key de MiniMax

1. En Render Dashboard → tu servicio → **Environment**
2. Click **Add Environment Variable**:
   - Key: `MINIMAX_API_KEY`
   - Value: `sk-...` (tu key real)
3. Click **Save Changes** → Render redespliega automáticamente

### 4. Abre tu chat

Tu URL será algo como:
```
https://vzla-search-bot.onrender.com
```

¡Listo! Comparte esa URL.

> **Nota:** en el free tier, el servicio "duerme" tras 15 minutos sin uso.
> El primer click tarda ~30-50 segundos en despertar; los siguientes son instantáneos.

---

## 🧪 Probarlo localmente antes de subir

Si quieres verificar antes de subir a Render:

```powershell
cd C:\Users\ZyosxD\.openclaw\workspace\venezuela-search-bot\backend

# Crear venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar deps
pip install -r requirements.txt

# Instalar Chromium para Playwright
playwright install chromium

# Configurar tu API key
$env:MINIMAX_API_KEY = "sk-..."

# Arrancar
uvicorn app:app --reload --port 8000
```

Abre http://localhost:8000 — el frontend se sirve desde la misma URL.

---

## 🔧 Añadir más plataformas

Para añadir una nueva plataforma al rotador:

1. Crea `backend/platforms/<nombre>.py` siguiendo el patrón de `desaparecidos.py`
2. Registra el adaptador en `backend/platforms/__init__.py`
3. Agrégala a `ENABLED_PLATFORMS` en `backend/app.py`
4. Commit + push → Render redespliega solo

Las plantillas `venezuelatebusca.py`, `statusvzla.py` y `icrc.py` tienen
selectores marcados con `TODO:` que necesitan validación contra el sitio
real antes de funcionar — inspecciona cada sitio con DevTools y ajusta.

---

## ⚠️ Limitaciones conocidas del MVP

- **Selectores no validados en 3 de 4 plataformas.** Solo `desaparecidos.py` está
  listo para inspección. Los otros 3 devolverán [] hasta que valides los
  selectores contra el DOM real (15 min por plataforma con DevTools).
- **Rate-limit ético.** 1 consulta = 4 requests a sitios de desastre. Si tu
  sitio recibe mucho tráfico, considera cachear resultados idénticos por 5 min
  (TODO: añadir Redis o dict en memoria).
- **Sin auth en la API.** Cualquiera puede hacer queries. Si abusa, añade
  Cloudflare Turnstile o un rate-limit por IP.
- **MiniMax API key obligatoria** para respuestas formateadas con IA. Sin key,
  el bot devuelve texto plano (sigue funcionando, solo menos bonito).

---

## 📋 Estructura

```
venezuela-search-bot/
├── render.yaml              # Render Blueprint (deploy config)
├── README.md                # Este archivo
├── .gitignore
├── backend/
│   ├── Dockerfile           # Imagen para Render
│   ├── requirements.txt
│   ├── app.py               # FastAPI principal
│   ├── ai_formatter.py      # Integración MiniMax API
│   └── platforms/
│       ├── __init__.py      # Registry
│       ├── base.py          # Interfaz abstracta
│       ├── _browser.py      # Pool compartido de Playwright
│       ├── desaparecidos.py # ✅ Adaptador de referencia (validar selectores)
│       ├── venezuelatebusca.py  # 📝 Template
│       ├── statusvzla.py        # 📝 Template
│       └── icrc.py              # 📝 Template
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js               # Chat UI bilingüe
```

---

## 🤝 Ética y editorial

Este bot sigue la política editorial del proyecto Canal Venezuela Terremoto 2026:

- **No almacena datos personales** (sin DB propia)
- **Atribución obligatoria** a cada plataforma fuente
- **Rate-limit ético** (1 plataforma a la vez, timeouts respetuosos)
- **Verificación institucional** preferida (Cruz Roja/ICRC como ancla oficial)
- **Si una fuente pide parar**, se quita del rotador

Si una familia o plataforma solicita remoción de algún dato, se desactiva
el adaptador correspondiente y se borra cualquier cache local.

---

**Mantenedor:** Zyos · Proyecto: Canal Venezuela Terremoto 2026
**Stack:** FastAPI · Playwright · MiniMax · Render · Vanilla JS