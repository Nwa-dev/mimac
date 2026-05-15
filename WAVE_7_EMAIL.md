# WAVE 7 — Email Sending

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1–6 are complete: scaffold, models, CRUD, PDFs, payment flow, and settings
are all working. This is Wave 7. Build ONLY what is specified here.

Email allows the business to send invoices to clients and automatically deliver receipts
on payment. All emails carry branded HTML templates and the relevant PDF attached.

---

## Objectives
- Build the email sending utility using `django.core.mail`
- Create branded HTML email templates for invoice and receipt emails
- Add a "Send Invoice" action on the invoice detail page
- Auto-send receipt email when an invoice is marked as paid
- Add a "Resend Receipt" action on the receipt detail page
- Wire up SMTP configuration via `.env`
- Fall back gracefully when email is not configured

---

## 1. Email Utility (`core/utils/email_utils.py`)

Replace the entire `core/utils/email_utils.py`:

```python
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from core.utils.pdf import generate_pdf

logger = logging.getLogger(__name__)


def send_invoice_email(invoice, request=None):
    """
    Send the invoice PDF to the client via email.

    Args:
        invoice: Invoice model instance
        request: Optional Django request (used to build absolute URLs)

    Returns:
        True if sent successfully, False otherwise
    """
    client = invoice.client

    if not client.email:
        logger.warning(f"Invoice {invoice.invoice_number}: client has no email address.")
        return False

    business = _get_business()
    from_email = _get_from_email(business)

    # Render HTML email body
    context = {
        'invoice':  invoice,
        'business': business,
    }
    html_body = render_to_string('core/email/invoice_email.html', context)

    # Generate PDF attachment
    pdf_bytes = generate_pdf('core/pdf/invoice.html', {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'INVOICE',
    })

    subject = f"Invoice {invoice.invoice_number} from {business.name if business else 'Us'}"

    try:
        email = EmailMessage(
            subject    = subject,
            body       = html_body,
            from_email = from_email,
            to         = [client.email],
        )
        email.content_subtype = 'html'  # Send as HTML
        email.attach(
            filename     = f"{invoice.invoice_number}.pdf",
            content      = pdf_bytes,
            mimetype     = 'application/pdf',
        )
        email.send(fail_silently=False)

        # Update invoice status to 'sent' if it was 'draft'
        if invoice.status == 'draft':
            invoice.status = 'sent'
            invoice.save(update_fields=['status'])

        logger.info(f"Invoice email sent: {invoice.invoice_number} → {client.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send invoice email {invoice.invoice_number}: {e}")
        return False


def send_receipt_email(invoice):
    """
    Send the receipt PDF to the client via email.
    Should only be called for paid invoices.

    Args:
        invoice: Invoice model instance (must have status='paid')

    Returns:
        True if sent successfully, False otherwise
    """
    if invoice.status != 'paid':
        logger.warning(f"Attempted to send receipt for unpaid invoice {invoice.invoice_number}")
        return False

    client = invoice.client

    if not client.email:
        logger.warning(f"Receipt {invoice.receipt_number}: client has no email address.")
        return False

    business = _get_business()
    from_email = _get_from_email(business)

    # Render HTML email body
    context = {
        'invoice':  invoice,
        'business': business,
    }
    html_body = render_to_string('core/email/receipt_email.html', context)

    # Generate receipt PDF attachment
    pdf_bytes = generate_pdf('core/pdf/invoice.html', {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'RECEIPT',
    })

    subject = f"Receipt {invoice.receipt_number} — Payment Confirmed"

    try:
        email = EmailMessage(
            subject    = subject,
            body       = html_body,
            from_email = from_email,
            to         = [client.email],
        )
        email.content_subtype = 'html'
        email.attach(
            filename = f"{invoice.receipt_number}.pdf",
            content  = pdf_bytes,
            mimetype = 'application/pdf',
        )
        email.send(fail_silently=False)
        logger.info(f"Receipt email sent: {invoice.receipt_number} → {client.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send receipt email {invoice.receipt_number}: {e}")
        return False


def _get_business():
    """Safe import to avoid circular imports."""
    from core.models import BusinessProfile
    return BusinessProfile.get_profile()


def _get_from_email(business):
    """Determine the FROM email address."""
    if business and business.email:
        name  = business.name
        email = business.email
        return f"{name} <{email}>"
    return settings.DEFAULT_FROM_EMAIL
```

---

## 2. Email Views (`core/views.py` — add these functions)

```python
from .utils.email_utils import send_invoice_email, send_receipt_email
from django.views.decorators.http import require_POST


@require_POST
def send_invoice(request, pk):
    """Send invoice PDF to client via email."""
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.warning(request, "This invoice is already paid. Send the receipt instead.")
        return redirect('core:invoice_detail', pk=pk)

    if not invoice.client.email:
        messages.error(
            request,
            f"Client '{invoice.client}' has no email address. "
            f"<a href='{% url 'core:client_edit' invoice.client.pk %}'>Add one here.</a>"
        )
        return redirect('core:invoice_detail', pk=pk)

    success = send_invoice_email(invoice, request)

    if success:
        messages.success(
            request,
            f"Invoice {invoice.invoice_number} sent to {invoice.client.email}."
        )
    else:
        messages.error(
            request,
            "Failed to send email. Check your email settings or try again."
        )

    return redirect('core:invoice_detail', pk=pk)


@require_POST
def send_receipt(request, pk):
    """Send receipt PDF to client via email."""
    invoice = get_object_or_404(Invoice, pk=pk, status='paid')

    if not invoice.client.email:
        messages.error(
            request,
            f"Client '{invoice.client}' has no email address. Add one to send the receipt."
        )
        return redirect('core:receipt_detail', pk=pk)

    success = send_receipt_email(invoice)

    if success:
        messages.success(
            request,
            f"Receipt {invoice.receipt_number} sent to {invoice.client.email}."
        )
    else:
        messages.error(
            request,
            "Failed to send email. Check your email settings or try again."
        )

    return redirect('core:receipt_detail', pk=pk)
```

**Note on the `messages.error` with HTML:** Django's `messages` framework escapes HTML by default.
If you want the "Add one here" link to work, use `mark_safe` and `extra_tags`, or simplify
the message to plain text and add a separate link on the template. The simpler approach
for Wave 7 is to use plain text messages only.

---

## 3. URL Patterns (`core/urls.py` — add these)

```python
path('invoices/<int:pk>/send/',          views.send_invoice, name='send_invoice'),
path('invoices/<int:pk>/send-receipt/',  views.send_receipt, name='send_receipt'),
```

---

## 4. Auto-Send Receipt After Payment

In `mark_as_paid` view, after successfully recording payment, automatically send the
receipt email (if the client has an email address):

```python
# Inside mark_as_paid view, after invoice.mark_as_paid() and redirect setup:

if form.is_valid():
    invoice.mark_as_paid(...)

    # Auto-send receipt email
    if invoice.client.email:
        sent = send_receipt_email(invoice)
        if sent:
            messages.success(
                request,
                f"✓ Payment recorded. Receipt emailed to {invoice.client.email}."
            )
        else:
            messages.success(
                request,
                "✓ Payment recorded. Receipt is ready (email could not be sent — check settings)."
            )
    else:
        messages.success(request, "✓ Payment recorded. Receipt is ready.")

    return redirect('core:receipt_detail', pk=invoice.pk)
```

---

## 5. Email HTML Templates

### `core/templates/core/email/invoice_email.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Invoice {{ invoice.invoice_number }}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      font-size: 14px;
      line-height: 1.6;
    }
    .wrapper {
      max-width: 580px;
      margin: 32px auto;
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    .header {
      background: #0f172a;
      padding: 28px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .header-brand { color: #ffffff; font-size: 18px; font-weight: 800; }
    .header-badge {
      background: #10b981;
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 20px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .body { padding: 32px; }
    .greeting { font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
    .message { color: #475569; margin-bottom: 28px; }
    .invoice-summary {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 28px;
    }
    .summary-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid #e2e8f0;
      font-size: 13px;
    }
    .summary-row:last-child { border-bottom: none; }
    .summary-label { color: #64748b; }
    .summary-value { font-weight: 600; color: #0f172a; }
    .total-row {
      display: flex;
      justify-content: space-between;
      padding: 12px 0 0;
      font-size: 16px;
      font-weight: 800;
      color: #0f172a;
    }
    .total-amount { color: #10b981; }
    .bank-block {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 28px;
    }
    .bank-title { font-size: 11px; font-weight: 700; color: #065f46; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
    .bank-detail { font-size: 13px; color: #166534; margin-bottom: 3px; }
    .bank-value { font-weight: 700; }
    .note { font-size: 13px; color: #64748b; font-style: italic; margin-bottom: 28px; }
    .footer {
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      padding: 20px 32px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
    }
    .footer a { color: #10b981; text-decoration: none; }
  </style>
</head>
<body>
<div class="wrapper">

  <!-- Header -->
  <div class="header">
    <div class="header-brand">
      {% if business %}{{ business.name }}{% else %}Invoice System{% endif %}
    </div>
    <div class="header-badge">Invoice</div>
  </div>

  <!-- Body -->
  <div class="body">
    <div class="greeting">Hello {{ invoice.client.name }},</div>
    <div class="message">
      Please find attached your invoice from
      <strong>{% if business %}{{ business.name }}{% else %}us{% endif %}</strong>.
      Payment is due by <strong>{{ invoice.due_date }}</strong>.
    </div>

    <!-- Invoice Summary -->
    <div class="invoice-summary">
      <div class="summary-row">
        <span class="summary-label">Invoice Number</span>
        <span class="summary-value">{{ invoice.invoice_number }}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">Issue Date</span>
        <span class="summary-value">{{ invoice.issue_date }}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">Due Date</span>
        <span class="summary-value">{{ invoice.due_date }}</span>
      </div>
      {% if invoice.tax_rate > 0 %}
      <div class="summary-row">
        <span class="summary-label">Subtotal</span>
        <span class="summary-value">₦{{ invoice.subtotal|floatformat:2 }}</span>
      </div>
      <div class="summary-row">
        <span class="summary-label">Tax ({{ invoice.tax_rate }}%)</span>
        <span class="summary-value">₦{{ invoice.tax_amount|floatformat:2 }}</span>
      </div>
      {% endif %}
      <div class="total-row">
        <span>Total Due</span>
        <span class="total-amount">₦{{ invoice.total_amount|floatformat:2 }}</span>
      </div>
    </div>

    <!-- Bank Details (if available) -->
    {% if business and business.bank_name %}
    <div class="bank-block">
      <div class="bank-title">Payment Information</div>
      <div class="bank-detail">Bank: <span class="bank-value">{{ business.bank_name }}</span></div>
      <div class="bank-detail">Account Name: <span class="bank-value">{{ business.account_name }}</span></div>
      <div class="bank-detail">Account Number: <span class="bank-value">{{ business.account_number }}</span></div>
    </div>
    {% endif %}

    <!-- Notes -->
    {% if invoice.notes %}
    <div class="note">Note: {{ invoice.notes }}</div>
    {% endif %}

    <div style="color: #475569; font-size: 13px;">
      The full invoice is attached to this email as a PDF.
      {% if business and business.invoice_footer_note %}
      <br><br>{{ business.invoice_footer_note }}
      {% endif %}
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    {% if business %}
    {{ business.name }}
    {% if business.phone %} · {{ business.phone }}{% endif %}
    {% if business.email %} · {{ business.email }}{% endif %}
    {% endif %}
    <br>
    This is an automated email. Please do not reply directly to this address.
  </div>

</div>
</body>
</html>
```

---

### `core/templates/core/email/receipt_email.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Receipt {{ invoice.receipt_number }}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      font-size: 14px;
      line-height: 1.6;
    }
    .wrapper {
      max-width: 580px;
      margin: 32px auto;
      background: #ffffff;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    .header {
      background: #0f172a;
      padding: 28px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .header-brand { color: #ffffff; font-size: 18px; font-weight: 800; }
    .header-badge {
      background: #10b981;
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 20px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .success-banner {
      background: linear-gradient(135deg, #065f46, #047857);
      padding: 24px 32px;
      text-align: center;
    }
    .success-icon {
      width: 52px;
      height: 52px;
      background: rgba(255,255,255,0.2);
      border: 2px solid rgba(255,255,255,0.5);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 12px;
      font-size: 22px;
      color: white;
    }
    .success-title { color: #ffffff; font-size: 20px; font-weight: 800; margin-bottom: 4px; }
    .success-sub { color: rgba(255,255,255,0.75); font-size: 13px; }
    .body { padding: 32px; }
    .greeting { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }
    .message { color: #475569; margin-bottom: 24px; font-size: 14px; }
    .amount-block {
      text-align: center;
      background: #f0fdf4;
      border: 2px solid #bbf7d0;
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 24px;
    }
    .amount-label { font-size: 11px; font-weight: 700; color: #065f46; text-transform: uppercase; letter-spacing: 0.06em; }
    .amount-value { font-size: 36px; font-weight: 900; color: #065f46; margin: 6px 0; }
    .payment-details {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 18px 20px;
      margin-bottom: 24px;
    }
    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 5px 0;
      font-size: 13px;
      border-bottom: 1px solid #e2e8f0;
    }
    .detail-row:last-child { border-bottom: none; }
    .detail-label { color: #64748b; }
    .detail-value { font-weight: 600; color: #0f172a; }
    .footer {
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      padding: 20px 32px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
    }
  </style>
</head>
<body>
<div class="wrapper">

  <!-- Header -->
  <div class="header">
    <div class="header-brand">
      {% if business %}{{ business.name }}{% else %}Invoice System{% endif %}
    </div>
    <div class="header-badge">Receipt</div>
  </div>

  <!-- Success Banner -->
  <div class="success-banner">
    <div class="success-icon">✓</div>
    <div class="success-title">Payment Confirmed</div>
    <div class="success-sub">{{ invoice.receipt_number }} · {{ invoice.paid_at|date:"d M Y" }}</div>
  </div>

  <!-- Body -->
  <div class="body">
    <div class="greeting">Hello {{ invoice.client.name }},</div>
    <div class="message">
      We have received your payment for invoice <strong>{{ invoice.invoice_number }}</strong>.
      Your receipt is attached to this email as a PDF.
    </div>

    <!-- Amount Paid -->
    <div class="amount-block">
      <div class="amount-label">Amount Paid</div>
      <div class="amount-value">₦{{ invoice.amount_received|floatformat:2 }}</div>
    </div>

    <!-- Payment Details -->
    <div class="payment-details">
      <div class="detail-row">
        <span class="detail-label">Receipt Number</span>
        <span class="detail-value">{{ invoice.receipt_number }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Invoice Number</span>
        <span class="detail-value">{{ invoice.invoice_number }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Payment Date</span>
        <span class="detail-value">{{ invoice.paid_at|date:"d M Y, H:i" }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">Payment Method</span>
        <span class="detail-value">{{ invoice.payment_method_display_label }}</span>
      </div>
      {% if invoice.payment_reference %}
      <div class="detail-row">
        <span class="detail-label">Reference</span>
        <span class="detail-value">{{ invoice.payment_reference }}</span>
      </div>
      {% endif %}
    </div>

    <div style="color: #475569; font-size: 13px;">
      {% if business and business.receipt_footer_note %}
      {{ business.receipt_footer_note }}
      {% else %}
      Thank you for your payment.
      {% endif %}
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    {% if business %}
    {{ business.name }}
    {% if business.phone %} · {{ business.phone }}{% endif %}
    {% if business.email %} · {{ business.email }}{% endif %}
    {% endif %}
    <br>
    This is an automated confirmation email. Please retain for your records.
  </div>

</div>
</body>
</html>
```

---

## 6. Wire Up Email Buttons on Templates

### Invoice Detail Page — Add "Send to Client" button

For invoices with status `draft` or `sent`, add this form/button in the action section:

```html
{% if invoice.client.email %}
<form method="post" action="{% url 'core:send_invoice' invoice.pk %}">
  {% csrf_token %}
  <button type="submit"
          class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-all active:scale-95">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
    </svg>
    Send to Client
  </button>
</form>
{% else %}
<div class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-700/50 border border-surface-600 text-slate-500 text-sm cursor-not-allowed">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
  </svg>
  No email on file
</div>
{% endif %}
```

### Receipt Detail Page — Add "Resend Receipt" button

In `core/templates/core/receipt_detail.html`, add this after the "Download Receipt PDF" button:

```html
{% if invoice.client.email %}
<form method="post" action="{% url 'core:send_receipt' invoice.pk %}">
  {% csrf_token %}
  <button type="submit"
          class="flex items-center justify-center gap-2 w-full py-3.5 rounded-2xl bg-surface-700 hover:bg-surface-600 text-slate-300 text-sm font-semibold transition-colors">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
    </svg>
    Resend Receipt Email
  </button>
</form>
{% endif %}
```

---

## 7. SMTP Configuration

Update `.env` with real SMTP credentials:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Your Business <your-gmail@gmail.com>
```

Update `settings.py` to read `EMAIL_BACKEND` from env:

```python
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'  # console fallback for dev
)
```

**Gmail setup note (for documentation only):**
To use Gmail SMTP, the business owner must enable 2FA on their Gmail account and generate
an App Password at `myaccount.google.com/apppasswords`. The App Password (16 chars) is
used as `EMAIL_HOST_PASSWORD`, NOT the regular Gmail password.

---

## 8. Graceful Fallback When Email is Not Configured

In `email_utils.py`, add this guard at the top of both send functions:

```python
from django.conf import settings

def send_invoice_email(invoice, request=None):
    # Check if email is actually configured
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        logger.info("Email backend is console — printing to terminal instead of sending.")
        # Still proceed: console backend prints to terminal, useful for dev

    if not getattr(settings, 'EMAIL_HOST_USER', ''):
        logger.warning("EMAIL_HOST_USER not configured. Email not sent.")
        return False
    ...
```

---

## Acceptance Criteria

Before marking Wave 7 complete, verify ALL of the following:

- [ ] "Send to Client" button appears on invoice detail page for unpaid invoices with client emails
- [ ] "Send to Client" shows disabled state when client has no email
- [ ] `POST /invoices/<pk>/send/` sends the invoice email and attaches the PDF
- [ ] After sending, success message shows the client's email address
- [ ] After marking as paid, receipt email is automatically attempted
- [ ] If client has email, success message confirms email was sent to their address
- [ ] If client has no email, success message says receipt is ready (no email sent)
- [ ] "Resend Receipt Email" button on receipt detail page sends the receipt again
- [ ] Invoice email HTML template renders correctly with business info and invoice summary
- [ ] Receipt email HTML template renders correctly with green payment confirmation banner
- [ ] PDF is attached to both emails with correct filename
- [ ] Console email backend prints email to terminal in development
- [ ] SMTP backend successfully sends real email when credentials are configured
- [ ] Failure to send email does NOT break the payment flow — only shows a warning message

---

## Do NOT do in this wave
- Do not build scheduled/automated overdue detection (Wave 8)
- Do not add bulk email sending
- Do not add email open tracking
