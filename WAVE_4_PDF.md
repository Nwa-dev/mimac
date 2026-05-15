# WAVE 4 — PDF Generation (Invoice & Receipt)

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1–3 are complete: scaffold, models, and all CRUD views are working. This is Wave 4.
Build ONLY what is specified here.

The PDFs generated in this wave are the core deliverables of the system. They must be
**branded, professional, and print-ready**. They will carry the business logo, full address,
client info, itemized table, and totals. The receipt PDF reuses the invoice template
with a clear "RECEIPT" header and a payment confirmation block.

---

## Objectives
- Complete the `generate_pdf()` utility in `core/utils/pdf.py`
- Build a professional HTML invoice PDF template
- Build a receipt PDF template (variant of invoice)
- Add PDF download views for both invoice and receipt
- Wire up the download buttons on the invoice detail page
- Serve PDFs as inline browser view OR direct download

---

## 1. PDF Utility (`core/utils/pdf.py`)

Replace the entire file:

```python
import os
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def generate_pdf(template_name: str, context: dict) -> bytes:
    """
    Render a Django HTML template to PDF bytes using WeasyPrint.

    Args:
        template_name: Path to Django template (e.g. 'core/pdf/invoice.html')
        context:       Template context dict

    Returns:
        Raw PDF bytes
    """
    font_config = FontConfiguration()
    html_string = render_to_string(template_name, context)

    # Base URL needed so WeasyPrint can resolve relative media/static file paths
    base_url = f"file://{settings.BASE_DIR}/"

    pdf_bytes = HTML(
        string=html_string,
        base_url=base_url
    ).write_pdf(
        font_config=font_config
    )
    return pdf_bytes
```

---

## 2. PDF Views (`core/views.py` — add these functions)

Add these two view functions to the existing `core/views.py`:

```python
from django.http import HttpResponse
from .utils.pdf import generate_pdf


def invoice_pdf(request, pk):
    """Generate and serve the invoice as a PDF."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk
    )
    business = BusinessProfile.get_profile()

    context = {
        'invoice':  invoice,
        'business': business,
        'document_type': 'INVOICE',
    }

    pdf_bytes = generate_pdf('core/pdf/invoice.html', context)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')

    # 'inline' opens in browser; 'attachment' forces download
    disposition = request.GET.get('download', 'inline')
    filename = f"{invoice.invoice_number}.pdf"
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'

    return response


def receipt_pdf(request, pk):
    """Generate and serve the receipt PDF for a paid invoice."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk,
        status='paid'  # Receipts only exist for paid invoices
    )
    business = BusinessProfile.get_profile()

    context = {
        'invoice':  invoice,
        'business': business,
        'document_type': 'RECEIPT',
    }

    pdf_bytes = generate_pdf('core/pdf/invoice.html', context)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')

    disposition = request.GET.get('download', 'inline')
    filename = f"{invoice.receipt_number}.pdf"
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'

    return response
```

---

## 3. Add PDF URL Patterns (`core/urls.py`)

Add to `urlpatterns`:

```python
path('invoices/<int:pk>/pdf/',     views.invoice_pdf, name='invoice_pdf'),
path('invoices/<int:pk>/receipt/', views.receipt_pdf, name='receipt_pdf'),
```

---

## 4. PDF Template (`core/templates/core/pdf/invoice.html`)

This single template renders both invoice and receipt. The `document_type` context
variable switches between "INVOICE" and "RECEIPT" modes.

Create `core/templates/core/pdf/invoice.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{{ document_type }} {{ invoice.invoice_number }}</title>
  <style>
    /* ─── RESET & BASE ─────────────────────────────────────────────────────── */
    * { margin: 0; padding: 0; box-sizing: border-box; }

    @page {
      size: A4;
      margin: 0;
    }

    body {
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      font-size: 10pt;
      color: #1a1a2e;
      background: #ffffff;
    }

    /* ─── PAGE SHELL ────────────────────────────────────────────────────────── */
    .page {
      width: 210mm;
      min-height: 297mm;
      padding: 0;
      position: relative;
      display: flex;
      flex-direction: column;
    }

    /* ─── HEADER BAND ───────────────────────────────────────────────────────── */
    .header-band {
      background: #0f172a;
      padding: 32px 40px 28px;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
    }

    .brand-block {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .logo-img {
      width: 56px;
      height: 56px;
      object-fit: contain;
      border-radius: 8px;
    }

    .logo-placeholder {
      width: 56px;
      height: 56px;
      background: #10b981;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 22pt;
      font-weight: 800;
    }

    .business-name {
      color: #ffffff;
      font-size: 16pt;
      font-weight: 800;
      letter-spacing: -0.3px;
    }

    .business-tagline {
      color: #94a3b8;
      font-size: 8pt;
      margin-top: 2px;
    }

    .doc-type-block {
      text-align: right;
    }

    .doc-type-label {
      color: #10b981;
      font-size: 24pt;
      font-weight: 900;
      letter-spacing: 2px;
      text-transform: uppercase;
    }

    .doc-number {
      color: #94a3b8;
      font-size: 9pt;
      margin-top: 4px;
    }

    /* ─── ACCENT STRIPE ─────────────────────────────────────────────────────── */
    .accent-stripe {
      height: 4px;
      background: linear-gradient(to right, #10b981, #059669, #0f172a);
    }

    /* ─── META SECTION ──────────────────────────────────────────────────────── */
    .meta-section {
      padding: 28px 40px;
      display: flex;
      justify-content: space-between;
      gap: 24px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
    }

    .meta-block { flex: 1; }

    .meta-label {
      font-size: 7pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748b;
      margin-bottom: 8px;
    }

    .meta-value {
      font-size: 10pt;
      color: #1a1a2e;
      font-weight: 500;
      line-height: 1.5;
    }

    .meta-value strong {
      font-size: 11pt;
      font-weight: 700;
      display: block;
      margin-bottom: 2px;
    }

    /* ─── STATUS BADGE ──────────────────────────────────────────────────────── */
    .status-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .status-paid    { background: #d1fae5; color: #065f46; }
    .status-sent    { background: #dbeafe; color: #1e40af; }
    .status-draft   { background: #f1f5f9; color: #475569; }
    .status-overdue { background: #fee2e2; color: #991b1b; }

    /* ─── CONTENT AREA ──────────────────────────────────────────────────────── */
    .content {
      flex: 1;
      padding: 32px 40px;
    }

    /* ─── LINE ITEMS TABLE ──────────────────────────────────────────────────── */
    .items-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 28px;
    }

    .items-table thead th {
      background: #0f172a;
      color: #94a3b8;
      font-size: 7.5pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 10px 12px;
      text-align: left;
    }

    .items-table thead th:last-child,
    .items-table thead th:nth-child(3),
    .items-table thead th:nth-child(2) {
      text-align: right;
    }

    .items-table tbody tr:nth-child(even) {
      background: #f8fafc;
    }

    .items-table tbody tr:nth-child(odd) {
      background: #ffffff;
    }

    .items-table tbody td {
      padding: 11px 12px;
      font-size: 9.5pt;
      color: #334155;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: top;
    }

    .items-table tbody td:nth-child(2),
    .items-table tbody td:nth-child(3),
    .items-table tbody td:nth-child(4) {
      text-align: right;
      white-space: nowrap;
    }

    .items-table tbody td:nth-child(4) {
      font-weight: 600;
      color: #1a1a2e;
    }

    .item-description { color: #1a1a2e; font-weight: 500; }

    /* ─── TOTALS BLOCK ──────────────────────────────────────────────────────── */
    .totals-wrapper {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 32px;
    }

    .totals-table {
      width: 240px;
    }

    .totals-row {
      display: flex;
      justify-content: space-between;
      padding: 5px 0;
      font-size: 9.5pt;
      color: #475569;
      border-bottom: 1px solid #e2e8f0;
    }

    .totals-row:last-child {
      border-bottom: none;
      background: #0f172a;
      color: #ffffff;
      font-weight: 700;
      font-size: 11pt;
      padding: 10px 12px;
      border-radius: 8px;
      margin-top: 6px;
    }

    .totals-row span:last-child { font-weight: 600; }

    /* ─── PAYMENT BLOCK (receipt only) ─────────────────────────────────────── */
    .payment-confirmed-block {
      background: #d1fae5;
      border: 2px solid #10b981;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 28px;
    }

    .payment-confirmed-title {
      color: #065f46;
      font-size: 13pt;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }

    .payment-confirmed-title::before {
      content: "✓";
      display: inline-flex;
      width: 22px;
      height: 22px;
      background: #10b981;
      color: white;
      border-radius: 50%;
      align-items: center;
      justify-content: center;
      font-size: 11pt;
      font-weight: 900;
    }

    .payment-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 16px;
    }

    .payment-field-label {
      font-size: 7pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #047857;
      margin-bottom: 3px;
    }

    .payment-field-value {
      font-size: 9.5pt;
      font-weight: 600;
      color: #064e3b;
    }

    /* ─── BANK DETAILS BLOCK ────────────────────────────────────────────────── */
    .bank-details-block {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 16px 20px;
      margin-bottom: 24px;
    }

    .bank-details-title {
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #64748b;
      margin-bottom: 10px;
    }

    .bank-details-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 12px;
    }

    .bank-field-label {
      font-size: 7pt;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 2px;
    }

    .bank-field-value {
      font-size: 9pt;
      font-weight: 600;
      color: #334155;
    }

    /* ─── NOTES BLOCK ───────────────────────────────────────────────────────── */
    .notes-block {
      margin-bottom: 24px;
    }

    .notes-label {
      font-size: 7.5pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #64748b;
      margin-bottom: 6px;
    }

    .notes-text {
      font-size: 9pt;
      color: #475569;
      line-height: 1.6;
    }

    /* ─── FOOTER ────────────────────────────────────────────────────────────── */
    .footer-band {
      background: #0f172a;
      padding: 18px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: auto;
    }

    .footer-note {
      color: #64748b;
      font-size: 8pt;
      line-height: 1.5;
    }

    .footer-brand {
      color: #10b981;
      font-size: 8pt;
      font-weight: 700;
    }

    /* ─── PRINT WATERMARK (draft) ───────────────────────────────────────────── */
    {% if invoice.status == 'draft' %}
    .page::after {
      content: 'DRAFT';
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-35deg);
      font-size: 90pt;
      font-weight: 900;
      color: rgba(0,0,0,0.04);
      letter-spacing: 10px;
      pointer-events: none;
      z-index: 0;
    }
    {% endif %}
  </style>
</head>
<body>
<div class="page">

  <!-- ─── HEADER BAND ─────────────────────────────────────────────────────── -->
  <div class="header-band">
    <div class="brand-block">
      {% if business and business.logo %}
        <img src="{{ business.logo.path }}" alt="Logo" class="logo-img" />
      {% else %}
        <div class="logo-placeholder">
          {% if business %}{{ business.name|first|upper }}{% else %}B{% endif %}
        </div>
      {% endif %}
      <div>
        <div class="business-name">
          {% if business %}{{ business.name }}{% else %}Your Business{% endif %}
        </div>
        {% if business and business.tagline %}
        <div class="business-tagline">{{ business.tagline }}</div>
        {% endif %}
      </div>
    </div>

    <div class="doc-type-block">
      <div class="doc-type-label">{{ document_type }}</div>
      <div class="doc-number">
        {% if document_type == 'RECEIPT' %}
          {{ invoice.receipt_number }}
        {% else %}
          {{ invoice.invoice_number }}
        {% endif %}
      </div>
    </div>
  </div>

  <!-- ─── ACCENT STRIPE ───────────────────────────────────────────────────── -->
  <div class="accent-stripe"></div>

  <!-- ─── META SECTION ────────────────────────────────────────────────────── -->
  <div class="meta-section">
    <!-- Business Details -->
    <div class="meta-block">
      <div class="meta-label">From</div>
      <div class="meta-value">
        {% if business %}
        <strong>{{ business.name }}</strong>
        {% if business.address_line1 %}{{ business.address_line1 }}<br>{% endif %}
        {% if business.address_line2 %}{{ business.address_line2 }}<br>{% endif %}
        {% if business.city %}{{ business.city }}{% if business.state %}, {{ business.state }}{% endif %}<br>{% endif %}
        {% if business.country %}{{ business.country }}<br>{% endif %}
        {% if business.phone %}Tel: {{ business.phone }}<br>{% endif %}
        {% if business.email %}{{ business.email }}{% endif %}
        {% if business.tax_id %}<br>TIN: {{ business.tax_id }}{% endif %}
        {% else %}
        <strong>Business Name</strong>
        Business address here
        {% endif %}
      </div>
    </div>

    <!-- Client Details -->
    <div class="meta-block">
      <div class="meta-label">Bill To</div>
      <div class="meta-value">
        <strong>{{ invoice.client }}</strong>
        {% if invoice.client.address_line1 %}{{ invoice.client.address_line1 }}<br>{% endif %}
        {% if invoice.client.address_line2 %}{{ invoice.client.address_line2 }}<br>{% endif %}
        {% if invoice.client.city %}
          {{ invoice.client.city }}{% if invoice.client.state %}, {{ invoice.client.state }}{% endif %}<br>
        {% endif %}
        {% if invoice.client.email %}{{ invoice.client.email }}<br>{% endif %}
        {% if invoice.client.phone %}Tel: {{ invoice.client.phone }}{% endif %}
      </div>
    </div>

    <!-- Invoice Dates & Status -->
    <div class="meta-block">
      <div class="meta-label">Details</div>
      <div class="meta-value">
        <div style="margin-bottom:6px;">
          <span style="color:#64748b; font-size:8pt;">Issue Date</span><br>
          <strong>{{ invoice.issue_date }}</strong>
        </div>
        {% if document_type == 'INVOICE' %}
        <div style="margin-bottom:6px;">
          <span style="color:#64748b; font-size:8pt;">Due Date</span><br>
          <strong {% if invoice.is_overdue %}style="color:#dc2626;"{% endif %}>{{ invoice.due_date }}</strong>
        </div>
        {% endif %}
        {% if document_type == 'RECEIPT' %}
        <div style="margin-bottom:6px;">
          <span style="color:#64748b; font-size:8pt;">Payment Date</span><br>
          <strong>{{ invoice.paid_at|date:"d M Y" }}</strong>
        </div>
        {% endif %}
        <div>
          <span style="color:#64748b; font-size:8pt;">Status</span><br>
          <span class="status-badge status-{{ invoice.status }}">{{ invoice.get_status_display }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ─── CONTENT ─────────────────────────────────────────────────────────── -->
  <div class="content">

    <!-- ─── PAYMENT CONFIRMED BLOCK (receipt only) ─────────────────────────── -->
    {% if document_type == 'RECEIPT' %}
    <div class="payment-confirmed-block">
      <div class="payment-confirmed-title">Payment Received</div>
      <div class="payment-grid">
        <div>
          <div class="payment-field-label">Amount Paid</div>
          <div class="payment-field-value">₦{{ invoice.amount_received|floatformat:2 }}</div>
        </div>
        <div>
          <div class="payment-field-label">Payment Method</div>
          <div class="payment-field-value">{{ invoice.payment_method_display_label }}</div>
        </div>
        <div>
          <div class="payment-field-label">Transaction Ref</div>
          <div class="payment-field-value">
            {% if invoice.payment_reference %}{{ invoice.payment_reference }}{% else %}—{% endif %}
          </div>
        </div>
      </div>
    </div>
    {% endif %}

    <!-- ─── LINE ITEMS TABLE ─────────────────────────────────────────────────── -->
    <table class="items-table">
      <thead>
        <tr>
          <th style="width:50%">Description</th>
          <th style="width:12%">Qty</th>
          <th style="width:19%">Unit Price</th>
          <th style="width:19%">Amount</th>
        </tr>
      </thead>
      <tbody>
        {% for item in invoice.items.all %}
        <tr>
          <td class="item-description">{{ item.description }}</td>
          <td>{{ item.quantity|floatformat:"-2" }}</td>
          <td>₦{{ item.unit_price|floatformat:2 }}</td>
          <td>₦{{ item.line_total|floatformat:2 }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <!-- ─── TOTALS ───────────────────────────────────────────────────────────── -->
    <div class="totals-wrapper">
      <div class="totals-table">
        <div class="totals-row">
          <span>Subtotal</span>
          <span>₦{{ invoice.subtotal|floatformat:2 }}</span>
        </div>
        {% if invoice.tax_rate > 0 %}
        <div class="totals-row">
          <span>Tax ({{ invoice.tax_rate }}%)</span>
          <span>₦{{ invoice.tax_amount|floatformat:2 }}</span>
        </div>
        {% endif %}
        <div class="totals-row">
          <span>Total</span>
          <span>₦{{ invoice.total_amount|floatformat:2 }}</span>
        </div>
      </div>
    </div>

    <!-- ─── BANK DETAILS (invoice only, not on receipt) ─────────────────────── -->
    {% if document_type == 'INVOICE' and business and business.bank_name %}
    <div class="bank-details-block">
      <div class="bank-details-title">Payment Information</div>
      <div class="bank-details-grid">
        <div>
          <div class="bank-field-label">Bank</div>
          <div class="bank-field-value">{{ business.bank_name }}</div>
        </div>
        <div>
          <div class="bank-field-label">Account Name</div>
          <div class="bank-field-value">{{ business.account_name }}</div>
        </div>
        <div>
          <div class="bank-field-label">Account Number</div>
          <div class="bank-field-value">{{ business.account_number }}</div>
        </div>
      </div>
    </div>
    {% endif %}

    <!-- ─── NOTES ────────────────────────────────────────────────────────────── -->
    {% if invoice.notes %}
    <div class="notes-block">
      <div class="notes-label">Notes</div>
      <div class="notes-text">{{ invoice.notes }}</div>
    </div>
    {% endif %}

  </div>

  <!-- ─── FOOTER BAND ──────────────────────────────────────────────────────── -->
  <div class="footer-band">
    <div class="footer-note">
      {% if document_type == 'RECEIPT' %}
        {% if business and business.receipt_footer_note %}{{ business.receipt_footer_note }}{% endif %}
      {% else %}
        {% if business and business.invoice_footer_note %}{{ business.invoice_footer_note }}{% endif %}
      {% endif %}
    </div>
    <div class="footer-brand">
      {{ invoice.invoice_number }}
    </div>
  </div>

</div>
</body>
</html>
```

---

## 5. Wire Up PDF Download Buttons on Invoice Detail Page

In `core/templates/core/invoice_detail.html`, update the action buttons section:

**For invoices that are NOT paid (`draft`, `sent`, `overdue`):**

```html
<!-- Download Invoice PDF (opens in browser) -->
<a href="{% url 'core:invoice_pdf' invoice.pk %}"
   target="_blank"
   class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-700 border border-surface-600 text-white text-sm font-medium hover:bg-surface-600 transition-colors">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z"/>
  </svg>
  View PDF
</a>

<!-- Download Invoice PDF as file -->
<a href="{% url 'core:invoice_pdf' invoice.pk %}?download=attachment"
   class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-700 border border-surface-600 text-white text-sm font-medium hover:bg-surface-600 transition-colors">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
  </svg>
  Download
</a>
```

**For paid invoices — show receipt buttons instead:**

```html
<!-- View Receipt PDF -->
<a href="{% url 'core:receipt_pdf' invoice.pk %}"
   target="_blank"
   class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold shadow-lg shadow-brand-500/30 transition-all active:scale-95">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z"/>
  </svg>
  View Receipt
</a>

<!-- Download Receipt PDF -->
<a href="{% url 'core:receipt_pdf' invoice.pk %}?download=attachment"
   class="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-700 border border-surface-600 text-white text-sm font-medium hover:bg-surface-600 transition-colors">
  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
  </svg>
  Download Receipt
</a>
```

---

## 6. Handle Logo Paths for WeasyPrint

WeasyPrint accesses files from disk. The logo `ImageField` provides a `.path` attribute
(absolute file path) and a `.url` attribute (web URL). In the PDF template, use `.path`
not `.url`, so WeasyPrint can read the file directly:

```html
<!-- Correct for WeasyPrint -->
<img src="{{ business.logo.path }}" ... />

<!-- Wrong — WeasyPrint cannot fetch HTTP URLs during PDF generation -->
<img src="{{ business.logo.url }}" ... />
```

This is already handled correctly in the template above.

---

## 7. Test PDF Generation

Test manually in Django shell:

```python
from core.models import Invoice, BusinessProfile
from core.utils.pdf import generate_pdf

invoice  = Invoice.objects.last()
business = BusinessProfile.get_profile()

context = {
    'invoice':       invoice,
    'business':      business,
    'document_type': 'INVOICE',
}

pdf_bytes = generate_pdf('core/pdf/invoice.html', context)
print(f"PDF size: {len(pdf_bytes)} bytes")

# Save to disk for visual inspection
with open('/tmp/test_invoice.pdf', 'wb') as f:
    f.write(pdf_bytes)
print("Saved to /tmp/test_invoice.pdf")
```

Open `/tmp/test_invoice.pdf` and verify:
- Business logo appears (or letter placeholder if no logo)
- Business name, address, contact info visible
- Client info populated
- Line items table renders correctly with descriptions, qty, price, total
- Subtotal, tax, and total amounts correct
- Footer note present
- No broken layout, no missing fonts

Repeat with `document_type: 'RECEIPT'` on a paid invoice and verify the green
payment confirmation block appears.

---

## Acceptance Criteria

Before marking Wave 4 complete, verify ALL of the following:

- [ ] `GET /invoices/<id>/pdf/` returns a valid PDF with `Content-Type: application/pdf`
- [ ] `GET /invoices/<id>/pdf/?download=attachment` triggers a file download
- [ ] `GET /invoices/<id>/receipt/` returns a valid PDF for a paid invoice
- [ ] `GET /invoices/<id>/receipt/` returns 404 for an unpaid invoice
- [ ] PDF contains business logo (or letter placeholder if no logo set)
- [ ] PDF contains business name, address, phone, email
- [ ] PDF contains client name and contact details
- [ ] PDF shows all line items with correct quantities, unit prices, and line totals
- [ ] Subtotal, tax, and total are mathematically correct
- [ ] Bank payment details appear on invoice PDF (if configured)
- [ ] Receipt PDF shows the green payment confirmation block with payment date, method, and reference
- [ ] Draft invoice PDF shows "DRAFT" watermark
- [ ] View/Download buttons on invoice detail page link to correct URLs
- [ ] Paid invoice detail page shows receipt PDF buttons instead of invoice PDF buttons

---

## Do NOT do in this wave
- Do not build the Mark as Paid flow (Wave 5)
- Do not send PDFs via email (Wave 7)
- Do not build the settings page (Wave 6)
