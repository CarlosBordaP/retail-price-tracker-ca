import requests
import logging

class Notifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(self.__class__.__name__)

    def send_notification(self, message: str):
        """Sends a notification to a webhook (Discord/Slack)."""
        if not self.webhook_url:
            self.logger.info(f"Notification (Dry Run): {message}")
            return

        try:
            payload = {"content": message}
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def notify_change(self, product_name: str, old_price: float, new_price: float):
        msg = f"🔔 **Price Alert**: {product_name} changed from ${old_price} to ${new_price}"
        self.send_notification(msg)
