import httpx
import logging
from typing import Dict, Any
from src.api.config import settings

logger = logging.getLogger("uba.webhook")

async def dispatch_siem_webhook(alert_data: Dict[str, Any]):
    """
    Dispatches a critical alert payload to the configured SIEM Webhook URL.
    """
    webhook_url = getattr(settings, "WEBHOOK_URL", "")
    if not webhook_url:
        logger.debug("SIEM Webhook triggered, but WEBHOOK_URL is not configured.")
        return

    payload = {
        "source": "UBA Insider Threat Engine",
        "type": "New Alert",
        "data": alert_data
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=5.0)
            if response.status_code >= 400:
                logger.error(f"Failed to push SIEM webhook to {webhook_url}. HTTP {response.status_code}: {response.text}")
            else:
                logger.info(f"SIEM Webhook dispatched successfully to {webhook_url} for user {alert_data.get('user_id')}")
    except httpx.RequestError as e:
        logger.error(f"Error while requesting {e.request.url!r}.")
    except Exception as e:
        logger.error(f"Unexpected error when dispatching SIEM webhook: {e}")
