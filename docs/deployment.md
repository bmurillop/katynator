# Guía de Despliegue

Esta guía lleva el sistema de cero a funcionando en tu red local, paso a paso.

---

## Requisitos previos

### 1. Docker Desktop

Docker es el programa que corre los tres servicios del sistema (base de datos, servidor, y la interfaz web) sin que tengas que instalar nada más.

- **Mac:** [Descargar Docker Desktop para Mac](https://www.docker.com/products/docker-desktop/)
- **Windows:** [Descargar Docker Desktop para Windows](https://www.docker.com/products/docker-desktop/) — requiere WSL2 (el instalador te guía)
- **Linux (Ubuntu/Debian):**
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  # Cierra sesión y vuelve a entrar
  ```

Verifica que funciona:
```bash
docker --version        # debe mostrar algo como "Docker version 26.x"
docker compose version  # debe mostrar "Docker Compose version 2.x"
```

### 2. Git

Para descargar el código.

- **Mac:** viene instalado, o instala desde [git-scm.com](https://git-scm.com)
- **Windows:** [git-scm.com/download/win](https://git-scm.com/download/win)
- **Linux:** `sudo apt install git`

### 3. Un correo dedicado (Gmail recomendado)

Crea una cuenta de Gmail nueva (o usa una existente) **solo para estados de cuenta**. Todos los miembros de la familia le reenviarán sus correos bancarios a esta dirección.

> **¿Por qué uno separado?** El sistema procesa *todo* lo que llega a esa bandeja. Un correo dedicado evita que analice correos personales.

### 4. Una API key de Gemini (gratis)

1. Ve a [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Inicia sesión con una cuenta de Google
3. Haz clic en **"Create API key"**
4. Copia la key — la necesitarás en la configuración

El nivel gratuito de Gemini es suficiente para el volumen de una familia.

---

## Instalación

### Paso 1 — Descargar el código

```bash
git clone https://github.com/bmurillop/katynator.git
cd katynator
```

### Paso 2 — Crear el archivo de configuración

```bash
cp .env.example .env
```

Abre `.env` con cualquier editor de texto y completa los valores. Las secciones siguientes explican cada uno.

### Paso 3 — Configurar la base de datos

Estas variables definen el usuario y contraseña de la base de datos interna. No son credenciales que vas a usar — son internas al sistema.

```env
POSTGRES_DB=financedb
POSTGRES_USER=finance
POSTGRES_PASSWORD=EligeUnaContraseñaSegura123
```

### Paso 4 — Configurar la clave secreta

Esta clave firma los tokens de sesión. Debe ser aleatoria y larga.

Genera una con este comando (si tienes Python instalado):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

O usa cualquier generador de contraseñas — 64 caracteres aleatorios sirven. Pega el resultado en:
```env
SECRET_KEY=pega_aqui_tu_clave_generada
```

### Paso 5 — Configurar el admin inicial

Estas son las credenciales con las que vas a entrar por primera vez. Después de tu primer ingreso, el sistema te pedirá cambiar la contraseña.

```env
ADMIN_EMAIL=tu@correo.com
ADMIN_PASSWORD=ContraseñaTemporal123
```

> Una vez que hayas iniciado sesión y cambiado la contraseña, puedes borrar `ADMIN_PASSWORD` del `.env` por seguridad. El sistema la ignora si ya existe un admin en la base de datos.

### Paso 6 — Configurar el correo IMAP

Esta es la cuenta de Gmail donde recibirás los estados de cuenta.

**Primero, activa el acceso IMAP en Gmail:**
1. Abre Gmail → Ajustes (ícono de engranaje) → "Ver todos los ajustes"
2. Pestaña **"Reenvío y correo POP/IMAP"**
3. En la sección IMAP, selecciona **"Habilitar IMAP"**
4. Guarda los cambios

**Luego, crea una contraseña de aplicación** (requerida porque Gmail bloquea contraseñas normales):
1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security)
2. En "Cómo inicias sesión en Google", activa la **Verificación en 2 pasos** si no está activada
3. Regresa a seguridad → busca **"Contraseñas de aplicaciones"** (aparece después de activar 2 pasos)
4. Selecciona "Otro (nombre personalizado)" → escribe "MY Finanzas" → haz clic en "Generar"
5. Copia la contraseña de 16 caracteres que aparece

```env
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=tucuenta@gmail.com
IMAP_PASSWORD=xxxx xxxx xxxx xxxx   # la contraseña de aplicación de 16 caracteres
IMAP_FOLDER=INBOX
IMAP_POLL_INTERVAL_MINUTES=5
```

### Paso 7 — Configurar el proveedor de IA

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...   # la key que copiaste de aistudio.google.com
```

Si prefieres Claude en lugar de Gemini:
```env
AI_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...
```

Si prefieres correr un modelo completamente local (sin internet) con LM Studio:
```env
AI_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
LMSTUDIO_MODEL=nombre-del-modelo
```

### Paso 8 — Iniciar el sistema

```bash
docker compose up -d
```

La primera vez toma unos minutos porque descarga las imágenes de Docker. Las siguientes veces es casi inmediato.

Verifica que todo corrió bien:
```bash
docker compose ps
```

Debes ver los tres servicios (`db`, `backend`, `frontend`) con estado `Up` o `healthy`.

Si algo falla, revisa los logs:
```bash
docker compose logs backend   # errores de configuración aparecen aquí
docker compose logs db
```

---

## Primer ingreso

1. Abre `http://localhost` en el navegador del computador donde instalaste Docker
2. Entra con el correo y contraseña que pusiste en `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. El sistema te pedirá cambiar la contraseña — hazlo
4. Ya estás adentro

---

## Configuración inicial

### Agregar miembros de la familia

1. Ve a **Configuración** → pestaña de usuarios (si está implementada) o usa la sección de personas
2. Crea un registro por cada miembro: nombre y correo
3. Cada cuenta bancaria se asociará a un miembro

### Agregar cuentas bancarias

El sistema crea las cuentas automáticamente la primera vez que procesa un estado de cuenta. También puedes crearlas manualmente en **Cuentas** → botón de agregar, especificando:
- El banco (entidad)
- El tipo de cuenta (corriente, ahorro, tarjeta de crédito)
- La moneda (colones o dólares — **no se puede cambiar después**)
- Los últimos 4 dígitos del número de cuenta

### Reenviar estados de cuenta

Para que el sistema empiece a procesar transacciones:
1. Cuando recibas un estado de cuenta bancario por correo, **reenvíalo** a la cuenta de Gmail configurada en `IMAP_USER`
2. El sistema lo detectará en los próximos 5 minutos y lo procesará automáticamente
3. Revisa la **Bandeja** para ver el resultado — si algo salió mal, aparecerá ahí con el error específico

> **Truco:** En Gmail puedes crear un filtro que reenvíe automáticamente correos de tu banco.

---

## Acceso desde otros dispositivos en la red

Por defecto, el sistema solo es accesible en `http://localhost` desde el mismo computador. Para acceder desde otros dispositivos (celular, laptop, etc.):

**Opción A — Por IP directa:**

Encuentra la IP del computador en tu red local:
- Mac: Ajustes del Sistema → Red → tu conexión → "Detalles"
- Windows: `ipconfig` en la terminal → busca "IPv4 Address"
- Linux: `ip addr`

Abre `http://192.168.1.X` (o la IP que encontraste) desde cualquier dispositivo en la misma red.

**Opción B — Por nombre (recomendado):**

Configura `finanzas.internal` en tu router para que apunte a la IP del computador. Así puedes acceder con `http://finanzas.internal` desde cualquier dispositivo.

Cómo hacerlo depende de tu router:
- **Routers con firmware estándar:** busca en la configuración del router "DNS local", "Static DNS", o "Host entries". Agrega: nombre `finanzas.internal` → IP del computador.
- **pfSense / OPNsense:** Services → DNS Resolver → Host Overrides
- **Pi-hole:** Local DNS → DNS Records
- **Sin acceso al router:** en cada dispositivo, edita el archivo `hosts` y agrega la línea `192.168.1.X finanzas.internal`
  - Mac/Linux: `/etc/hosts`
  - Windows: `C:\Windows\System32\drivers\etc\hosts`

---

## Actualizar el sistema

Cuando haya cambios en el código:

```bash
git pull
docker compose up -d --build
```

Las migraciones de base de datos corren automáticamente al iniciar. Tus datos no se borran.

---

## Respaldar los datos

Los datos viven en un volumen de Docker llamado `pgdata`. Para respaldarlo:

```bash
# Crear un respaldo
docker compose exec db pg_dump -U finance financedb > respaldo_$(date +%Y%m%d).sql

# Restaurar desde un respaldo
cat respaldo_20260101.sql | docker compose exec -T db psql -U finance financedb
```

Se recomienda hacer esto antes de actualizar.

---

## Apagar y reiniciar

```bash
# Apagar (los datos se conservan)
docker compose down

# Reiniciar
docker compose up -d

# Apagar y borrar TODO (¡incluidos los datos!)
docker compose down -v   # cuidado con -v
```

---

## Solución de problemas

### El sistema no inicia / los logs muestran errores de conexión

```bash
docker compose logs backend
```

Los errores más comunes:
- **`could not connect to server`** — la base de datos tardó en iniciar. Espera 30 segundos y vuelve a intentar `docker compose up -d`
- **`DATABASE_URL missing`** — el archivo `.env` no existe o está mal nombrado
- **`invalid input value for enum`** — migración fallida, intenta `docker compose exec backend alembic upgrade head`

### El correo no se está procesando

1. Verifica que `IMAP_USER` y `IMAP_PASSWORD` son correctos
2. Confirma que activaste IMAP en Gmail (Paso 6)
3. Confirma que la contraseña en `.env` es la **contraseña de aplicación** de 16 dígitos, no tu contraseña de Gmail normal
4. Revisa `docker compose logs backend` — los errores de IMAP aparecen ahí

### La IA no extrae las transacciones correctamente

Usa la herramienta CLI para probar sin correr el sistema completo:

```bash
docker compose exec backend python -m app.tools.parse_pdf /ruta/al/estado.pdf
```

O desde fuera del contenedor (con Python instalado localmente):
```bash
cd backend
GEMINI_API_KEY=tu-key python -m app.tools.parse_pdf /ruta/al/estado.pdf --raw
```

El flag `--raw` muestra la respuesta completa del modelo para diagnosticar qué salió mal.

### Ver todos los logs en tiempo real

```bash
docker compose logs -f
```
