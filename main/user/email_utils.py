import resend
import threading
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import strip_tags


class EmailHelper:
    """
    Helper class for sending transactional emails via Resend API.
    Runs async in a separate thread to avoid blocking request flow.
    """

    def __init__(self):
        self.api_key = getattr(settings, "RESEND_API_KEY", None)
        if not self.api_key:
            raise ImproperlyConfigured("RESEND_API_KEY not found in Django settings.")
        resend.api_key = self.api_key

    def send_email(
        self,
        subject: str,
        to,
        html_content: str,
        text_content: str = None,
        from_name: str = "Atut Vidhan",
        from_email: str = None,
        async_send: bool = True,
    ):
        from_email = "no-reply@lakshayjindal.xyz"
        """
        Send an email using Resend API.

        Args:
            subject (str): Subject line
            to (str | list): Recipient(s)
            html_content (str): HTML email body
            text_content (str): Plain text fallback (auto-generated if None)
            from_name (str): Sender display name
            from_email (str): Sender address (default = settings.DEFAULT_FROM_EMAIL)
            async_send (bool): Send asynchronously (True by default)
        """

        if isinstance(to, str):
            to = [to]

        sender_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@yourdomain.com")
        sender = f"{from_name} <{sender_email}>"

        # fallback text if not given
        text_content = text_content or strip_tags(html_content)

        params = {
            "from": sender,
            "to": to,
            "subject": subject,
            "html": html_content,
            "text": text_content,
        }

        def _send():
            try:
                email = resend.Emails.send(params)
                print(f"[Resend] ✅ Sent to {to}: {email.get('id', 'no-id')}")
                return {"success": True, "id": email.get("id"), "to": to}
            except Exception as e:
                print(f"[Resend] ❌ Error sending email: {e}")
                return {"success": False, "error": str(e)}

        if async_send:
            threading.Thread(target=_send, daemon=True).start()
            return {"success": True, "async": True}
        else:
            return _send()
