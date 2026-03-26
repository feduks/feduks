# USCIS Case Status Monitor

Consulta automática del estado de trámites USCIS para los casos:
`IOE0936110074` – `IOE0936110079`

## Instalación

```bash
pip install -r requirements.txt
```

## Uso manual

```bash
python check_uscis.py
```

La primera vez guarda el estado en `uscis_last_states.json`.
Las siguientes corridas detectan y loguean cualquier cambio.

## Configurar cron (2 veces al día: 9 AM y 6 PM)

```bash
crontab -e
```

Agregar:
```
0 9,18 * * * cd /ruta/al/proyecto && python check_uscis.py >> uscis.log 2>&1
```

## Notificaciones por email (opcional)

Exportar las siguientes variables de entorno antes de correr el script
(o agregarlas en el cron):

```bash
export USCIS_EMAIL_ENABLED=true
export USCIS_SMTP_HOST=smtp.gmail.com       # o tu servidor SMTP
export USCIS_SMTP_PORT=587
export USCIS_EMAIL_USER=tu@gmail.com
export USCIS_EMAIL_PASS=tu_app_password     # Gmail: usar App Password
export USCIS_EMAIL_TO=destino@gmail.com
```

En el cron quedaría así:
```
0 9,18 * * * cd /ruta/al/proyecto && USCIS_EMAIL_ENABLED=true USCIS_EMAIL_USER=tu@gmail.com USCIS_EMAIL_PASS=xxx USCIS_EMAIL_TO=tu@gmail.com python check_uscis.py >> uscis.log 2>&1
```

> **Gmail**: necesitás habilitar verificación en dos pasos y crear un
> [App Password](https://myaccount.google.com/apppasswords) específico.

## Archivo de estados

`uscis_last_states.json` guarda el último estado conocido de cada caso.
El script solo notifica cuando el estado cambia respecto a esa última lectura.
