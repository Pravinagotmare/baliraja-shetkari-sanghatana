import json
import re
import urllib.error
import urllib.request
from config import setting


_DIGIT_TRANSLATION = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_indian_mobile(value):
    digits = re.sub(r"\D", "", str(value or "").translate(_DIGIT_TRANSLATION))
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        return "91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return None


def configuration():
    return {
        "access_token": setting("WHATSAPP_ACCESS_TOKEN", "").strip(),
        "phone_number_id": setting("WHATSAPP_PHONE_NUMBER_ID", "").strip(),
        "api_version": setting("WHATSAPP_API_VERSION", "").strip(),
        "template_name": setting("WHATSAPP_TEMPLATE_NAME", "").strip(),
        "template_language": setting("WHATSAPP_TEMPLATE_LANGUAGE", "").strip(),
    }


def missing_configuration(config):
    return [key for key, value in config.items() if not value]


def send_template_message(config, recipient, message):
    url = (
        f"https://graph.facebook.com/{config['api_version']}/"
        f"{config['phone_number_id']}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": config["template_name"],
            "language": {"code": config["template_language"]},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": message}],
            }],
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        messages = result.get("messages") or []
        return messages[0].get("id") if messages else None, None
    except urllib.error.HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8"))
            error = details.get("error", {}).get("message", "WhatsApp API विनंती अयशस्वी.")
        except Exception:
            error = "WhatsApp API विनंती अयशस्वी."
        return None, str(error)[:1000]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, str(exc)[:1000]
