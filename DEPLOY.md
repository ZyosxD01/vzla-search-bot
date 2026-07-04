# Despliegue en servidor Linux propio (Cloudflare Tunnel)

Este proyecto corre en Docker. Cloudflare Tunnel expone `buscar.zyosdigital.com`
sin abrir ningún puerto público en el servidor — el contenedor solo escucha
en `127.0.0.1:8000`, y `cloudflared` reenvía el tráfico del túnel hacia ahí.

## 1. Requisitos en el servidor

- Docker + Docker Compose plugin (`docker compose version` debe funcionar).
- `cloudflared` ya instalado y el túnel ya creado y enrutado a
  `buscar.zyosdigital.com` (asumido, según lo indicado).

## 2. Clonar / actualizar el código

```bash
git clone <url-del-repo> vzla-bot   # primera vez
cd vzla-bot
git pull                            # actualizaciones siguientes
```

## 3. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
nano backend/.env   # completa MINIMAX_API_KEY como mínimo
```

`backend/.env` está en `.gitignore` — nunca se sube al repo.

## 4. Construir y levantar el contenedor

```bash
docker compose build
docker compose up -d
docker compose logs -f vzla-search   # verificar que arrancó bien
```

Verificación local (sin pasar por Cloudflare todavía):

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","platforms":[...13 plataformas...]}
```

## 5. Apuntar el túnel de Cloudflare al contenedor

En la configuración del túnel (`~/.cloudflared/config.yml` o el equivalente
si usas el dashboard de Zero Trust), el ingress para este hostname debe
apuntar al puerto local publicado por Compose:

```yaml
tunnel: <tu-tunnel-id>
credentials-file: /root/.cloudflared/<tu-tunnel-id>.json

ingress:
  - hostname: buscar.zyosdigital.com
    service: http://localhost:8000
  - service: http_status:404
```

Si editaste `config.yml`, reinicia el servicio:

```bash
sudo systemctl restart cloudflared
```

Si el túnel se administra desde el dashboard (Zero Trust → Networks →
Tunnels → Public Hostname), el equivalente es: **Public Hostname** =
`buscar.zyosdigital.com`, **Service** = `HTTP` → `localhost:8000`.

## 6. Verificar en producción

```bash
curl -s https://buscar.zyosdigital.com/health
```

Y abrir `https://buscar.zyosdigital.com/` en el navegador — debe cargar el
chat con el mensaje de bienvenida mencionando "13 plataformas".

## 7. Actualizar después de cambios de código

```bash
git pull
docker compose build
docker compose up -d
```

## Notas de memoria (Playwright)

El bot corre 9 de las 13 plataformas con un navegador Chromium headless
(las otras 4 — `statusvzla`, `icrc`, y las que no requieren scraping —
no usan navegador). `PLAYWRIGHT_CONCURRENCY = 3` en
[backend/app.py](backend/app.py) limita a 3 contextos de navegador
simultáneos para no saturar RAM; si el servidor tiene bastante memoria
libre (a diferencia del free tier de Render, para el cual se fijó ese
límite), puedes subir ese número para acelerar las búsquedas.
