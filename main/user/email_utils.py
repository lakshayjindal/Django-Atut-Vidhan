# utils/email_utils.py

from brevo_python import Configuration, ApiClient
from brevo_python.api.transactional_emails_api import TransactionalEmailsApi
from brevo_python.models.send_smtp_email import SendSmtpEmail
from django.conf import settings

def send_brevo_email(subject, text_content, from_email, to_list, html_content=None):
    """
    A drop-in replacement for Django's EmailMultiAlternatives using Brevo API.
    Example:
        send_brevo_email(subject, text, from_email, [to_email], html_content)
    """
    # Configure Brevo client
    config = Configuration()
    config.api_key['api-key'] = settings.BREVO_API_KEY

    with ApiClient(config) as api_client:
        api_instance = TransactionalEmailsApi(api_client)

        # Build Brevo email payload
        to_emails = [{"email": email} for email in to_list]
        sender_info = {"email": from_email, "name": "Atut Vidhan"}

        email_data = SendSmtpEmail(
            sender=sender_info,
            to=to_emails,
            subject=subject,
            html_content=html_content or text_content,
            text_content=text_content,
        )

        try:
            response = api_instance.send_transac_email(email_data)
            print("✅ Email sent successfully via Brevo:", response)
            return True
        except Exception as e:
            print("❌ Brevo email sending failed:", e)
            return False
