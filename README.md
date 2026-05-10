# MY Finanzas

Un rastreador de finanzas personales auto-hospedado para la familia. Monitorea un correo compartido, extrae las transacciones de los estados de cuenta bancarios con IA, y presenta un panel en español con soporte para colones y dólares.

**Corre completamente en tu red local** — la única conexión hacia internet es el correo y la API de IA.

---

## ¿Qué hace?

1. **Revisa un correo cada 5 minutos** buscando estados de cuenta bancarios que le reenvíes.
2. **Extrae las transacciones automáticamente** usando IA (Gemini, Claude, o un modelo local con LM Studio).
3. **Valida los totales** contra los del banco antes de guardar — si hay discrepancia, lo marca para revisión.
4. **Aprende con el tiempo**: asigna categorías basándose en quién pagó y el texto de la descripción, y recuerda tus preferencias.
5. **Muestra un panel** con tus cuentas, gastos del mes, y gráficas — colones y dólares siempre separados.

---

## Contenido

| | |
|---|---|
| **[Guía de despliegue](docs/deployment.md)** | Instalar y poner a correr el sistema desde cero |
| **[Arquitectura](docs/architecture.md)** | Cómo funciona internamente (para técnicos y agentes de IA) |
| **[Guía de desarrollo](docs/development.md)** | Cómo continuar el desarrollo, tests, y herramientas CLI |
| **[Estado del proyecto](docs/phases.md)** | Qué está listo y qué falta |

---

## Inicio rápido (para quien ya sabe Docker)

```bash
git clone https://github.com/bmurillop/katynator.git
cd katynator
cp .env.example .env
# Edita .env — ver docs/deployment.md para instrucciones detalladas
docker compose up -d
```

Abre `http://localhost` (o `http://finanzas.internal` si configuraste DNS en el router).

---

## Requisitos

- **Un computador encendido 24/7** con Docker instalado (Linux, Mac, o Windows con WSL2)
- **Un correo dedicado** (Gmail funciona) donde reenviarás los estados de cuenta
- **Una API key de Gemini** (gratuita) — o Claude API, o LM Studio local

---

## Estado del proyecto

| Fase | Estado |
|---|---|
| Infraestructura Docker + base de datos + autenticación | ✅ Completo |
| Proveedores de IA (Gemini, Claude, LM Studio) | ✅ Completo |
| Pipeline de correo → PDF → IA → transacciones | ✅ Completo |
| API REST completa | ✅ Completo |
| Interfaz web (panel, transacciones, cuentas, entidades, categorías) | ✅ Completo |
| Bandeja de entrada (entidades sin resolver, revisión, correos fallidos) | ✅ Completo |
| Sugerencias de categoría con IA + confirmación en la bandeja | ✅ Completo |
| Reglas de categorización (crear, editar, re-aplicar, transferencias) | ✅ Completo |
| Panel de transacciones internas (is_transfer) | ✅ Completo |
| Página de reportes + gráficas avanzadas | 🔲 Pendiente |
| Página de emails procesados | 🔲 Pendiente |
| Gestión de usuarios (admin) | 🔲 Pendiente |
| Pulido mobile | 🔲 Pendiente |

Ver detalles completos → [`docs/phases.md`](docs/phases.md)

---

## Tecnología

- **Backend:** Python + FastAPI + PostgreSQL + Alembic
- **Frontend:** React + Vite + Tailwind CSS + Tremor
- **IA:** Gemini (por defecto), Claude, o LM Studio
- **Contenedores:** Docker Compose (3 servicios: db, backend, frontend)
- **Extracción de PDF:** pdfplumber (sin OCR — todos los bancos objetivo generan PDFs de texto)
