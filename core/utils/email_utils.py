import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from core.utils.pdf import generate_pdf

logger = logging.getLogger(__name__)


def send_invoice_email(invoice, request=None):
    client = invoice.client

    if not client.email:
        logger.warning(f"Invoice {invoice.invoice_number}: client has no email address.")
        return False

    # For non-console backends, require EMAIL_HOST_USER to be configured
    is_console = settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    if not is_console and not getattr(settings, 'EMAIL_HOST_USER', ''):
        logger.warning("EMAIL_HOST_USER not configured. Email not sent.")
        return False

    business = _get_business()
    from_email = _get_from_email(business)

    context = {'invoice': invoice, 'business': business}
    html_body = render_to_string('core/email/invoice_email.html', context)

    pdf_bytes = generate_pdf('core/pdf/invoice.html', {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'INVOICE',
    })

    subject = f"Invoice {invoice.invoice_number} from {business.name if business else 'Us'}"

    try:
        email = EmailMessage(
            subject=subject,
            body=html_body,
            from_email=from_email,
            to=[client.email],
        )
        email.content_subtype = 'html'
        email.attach(
            filename=f"{invoice.invoice_number}.pdf",
            content=pdf_bytes,
            mimetype='application/pdf',
        )
        email.send(fail_silently=False)

        if invoice.status == 'draft':
            invoice.status = 'sent'
            invoice.save(update_fields=['status'])

        logger.info(f"Invoice email sent: {invoice.invoice_number} → {client.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send invoice email {invoice.invoice_number}: {e}")
        return False


def send_receipt_email(invoice):
    if invoice.status != 'paid':
        logger.warning(f"Attempted to send receipt for unpaid invoice {invoice.invoice_number}")
        return False

    client = invoice.client

    if not client.email:
        logger.warning(f"Receipt {invoice.receipt_number}: client has no email address.")
        return False

    is_console = settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    if not is_console and not getattr(settings, 'EMAIL_HOST_USER', ''):
        logger.warning("EMAIL_HOST_USER not configured. Email not sent.")
        return False

    business = _get_business()
    from_email = _get_from_email(business)

    context = {'invoice': invoice, 'business': business}
    html_body = render_to_string('core/email/receipt_email.html', context)

    pdf_bytes = generate_pdf('core/pdf/invoice.html', {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'RECEIPT',
    })

    subject = f"Receipt {invoice.receipt_number} — Payment Confirmed"

    try:
        email = EmailMessage(
            subject=subject,
            body=html_body,
            from_email=from_email,
            to=[client.email],
        )
        email.content_subtype = 'html'
        email.attach(
            filename=f"{invoice.receipt_number}.pdf",
            content=pdf_bytes,
            mimetype='application/pdf',
        )
        email.send(fail_silently=False)
        logger.info(f"Receipt email sent: {invoice.receipt_number} → {client.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send receipt email {invoice.receipt_number}: {e}")
        return False


def _get_business():
    from core.models import BusinessProfile
    return BusinessProfile.get_profile()


def _get_from_email(business):
    if business and business.email:
        return f"{business.name} <{business.email}>"
    return settings.DEFAULT_FROM_EMAIL
