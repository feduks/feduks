#!/usr/bin/env python3
"""
USCIS Case Status Monitor
Consulta el estado de los trámites en USCIS y notifica cambios por email.
"""

import os
import json
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Configuración ──────────────────────────────────────────────────────────────

CASE_NUMBERS = [
    "IOE0936110074",
    "IOE0936110075",
    "IOE0936110076",
    "IOE0936110077",
    "IOE0936110078",
    "IOE0936110079",
]

USCIS_URL = "https://egov.uscis.gov/casestatus/mycasestatus.do"

# Archivo donde se guardan los últimos estados conocidos
STATE_FILE = Path(__file__).parent / "uscis_last_states.json"

# Configuración de email (leer desde variables de entorno)
EMAIL_ENABLED = os.getenv("USCIS_EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SMTP_HOST = os.getenv("USCIS_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("USCIS_SMTP_PORT", "587"))
EMAIL_USER = os.getenv("USCIS_EMAIL_USER", "")
EMAIL_PASS = os.getenv("USCIS_EMAIL_PASS", "")
EMAIL_TO = os.getenv("USCIS_EMAIL_TO", "")

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Funciones principales ──────────────────────────────────────────────────────

def fetch_case_status(receipt_number: str) -> dict:
    """Consulta el estado de un caso en USCIS y devuelve título y detalle."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Referer": "https://egov.uscis.gov/casestatus/landing.do",
        "Origin": "https://egov.uscis.gov",
    }
    payload = {
        "appReceiptNum": receipt_number,
        "caseStatusSearchBtn": "CHECK STATUS",
    }

    try:
        resp = requests.post(
            USCIS_URL,
            data=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Error al consultar %s: %s", receipt_number, exc)
        return {"receipt": receipt_number, "title": "ERROR", "detail": str(exc)}

    soup = BeautifulSoup(resp.text, "html.parser")

    # El status principal está en: div.rows > div.text-center > h1
    title_tag = soup.select_one("div.rows h1")
    title = title_tag.get_text(strip=True) if title_tag else "No se encontró el título"

    # El detalle está en el <p> dentro del mismo bloque
    detail_tag = soup.select_one("div.rows p")
    detail = detail_tag.get_text(strip=True) if detail_tag else ""

    return {
        "receipt": receipt_number,
        "title": title,
        "detail": detail,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def load_last_states() -> dict:
    """Carga los estados guardados en disco. Devuelve {} si no existe el archivo."""
    if STATE_FILE.exists():
        with STATE_FILE.open() as f:
            return json.load(f)
    return {}


def save_states(states: dict) -> None:
    """Guarda los estados actuales en disco."""
    with STATE_FILE.open("w") as f:
        json.dump(states, f, indent=2, ensure_ascii=False)


def send_email_notification(changes: list[dict]) -> None:
    """Envía un email con los casos que cambiaron de estado."""
    if not EMAIL_ENABLED or not EMAIL_USER or not EMAIL_TO:
        log.info("Notificación email deshabilitada o sin configurar.")
        return

    subject = f"USCIS - Cambio de estado detectado ({len(changes)} caso/s)"
    body_lines = ["Se detectaron cambios en los siguientes casos USCIS:\n"]
    for ch in changes:
        body_lines.append(f"  Caso: {ch['receipt']}")
        body_lines.append(f"  Estado anterior: {ch['old_title']}")
        body_lines.append(f"  Estado nuevo:    {ch['new_title']}")
        body_lines.append(f"  Detalle: {ch['detail']}")
        body_lines.append(f"  Verificado: {ch['checked_at']}\n")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText("\n".join(body_lines), "plain", "utf-8"))

    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        log.info("Email enviado a %s", EMAIL_TO)
    except Exception as exc:
        log.error("No se pudo enviar el email: %s", exc)


# ── Flujo principal ────────────────────────────────────────────────────────────

def main():
    log.info("=== Iniciando consulta de estados USCIS ===")
    last_states = load_last_states()
    current_states = {}
    changes = []

    for receipt in CASE_NUMBERS:
        result = fetch_case_status(receipt)
        current_states[receipt] = result

        old_title = last_states.get(receipt, {}).get("title", "")
        new_title = result["title"]

        status_icon = "✓" if "ERROR" not in new_title else "✗"
        log.info("[%s] %s → %s", status_icon, receipt, new_title)

        if old_title and old_title != new_title:
            log.info("  *** CAMBIO DETECTADO: '%s' → '%s'", old_title, new_title)
            changes.append({
                **result,
                "old_title": old_title,
                "new_title": new_title,
            })

    save_states(current_states)
    log.info("Estados guardados en %s", STATE_FILE)

    if changes:
        log.info("Se detectaron %d cambio(s). Enviando notificación...", len(changes))
        send_email_notification(changes)
    else:
        log.info("Sin cambios desde la última consulta.")

    log.info("=== Consulta finalizada ===")


if __name__ == "__main__":
    main()
