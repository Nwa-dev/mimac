# WAVE 5 — Payment Flow

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1–4 are complete: scaffold, models, CRUD views, and PDF generation all working.
This is Wave 5. Build ONLY what is specified here.

The payment flow is the most critical transition in the system. When a client pays,
the invoice transitions to "paid" and a receipt becomes available. This wave builds
that transition — the "Mark as Paid" button, the payment form modal, the confirmation,
and the redirect to the receipt view.

---

## Objectives
- Build the "Mark as Paid" form and view
- Build a receipt detail page (the web view of a receipt, not the PDF)
- Handle edge cases: double payment, cancellation
- Add a payment confirmation success page/redirect flow
- Make the payment modal mobile-friendly and tactile

---

## 1. Payment Form (`core/forms.py` — add this form)

Add `MarkAsPaidForm` to `core/forms.py`:

```python
from django import forms
from django.utils import timezone
from .models import Invoice


class MarkAsPaidForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=Invoice.PAYMENT_METHOD_CHOICES,
        widget=forms.Select()
    )
    amount_received = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'placeholder': '0.00',
        })
    )
    paid_at = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeLocalInput(attrs={
            'type': 'datetime-local'
        })
    )
    payment_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Transaction ID, cheque no., etc. (optional)'
        })
    )
```

**Note for Claude Code:** Django does not have a built-in `DateTimeLocalInput`.
Use `forms.DateTimeInput` with `attrs={'type': 'datetime-local'}` and set the
input format accordingly:

```python
paid_at = forms.DateTimeField(
    input_formats=['%Y-%m-%dT%H:%M'],
    widget=forms.DateTimeInput(
        attrs={'type': 'datetime-local'},
        format='%Y-%m-%dT%H:%M'
    )
)
```

Set the initial value to current local datetime formatted correctly:

```python
import datetime
from django.utils import timezone

def __init__(self, *args, **kwargs):
    invoice_total = kwargs.pop('invoice_total', None)
    super().__init__(*args, **kwargs)
    now = timezone.localtime(timezone.now())
    self.fields['paid_at'].initial = now.strftime('%Y-%m-%dT%H:%M')
    if invoice_total:
        self.fields['amount_received'].initial = invoice_total
```

---

## 2. Payment Views (`core/views.py` — add these functions)

Add to `core/views.py`:

```python
from .forms import MarkAsPaidForm
import datetime


def mark_as_paid(request, pk):
    """
    GET:  Display the payment form for an invoice
    POST: Record payment, transition invoice to paid, redirect to receipt
    """
    invoice = get_object_or_404(Invoice, pk=pk)

    # Guard: only unpaid invoices can be paid
    if invoice.status == 'paid':
        messages.info(request, f"Invoice {invoice.invoice_number} is already marked as paid.")
        return redirect('core:invoice_detail', pk=pk)

    if invoice.status == 'cancelled':
        messages.error(request, "A cancelled invoice cannot be marked as paid.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        form = MarkAsPaidForm(request.POST, invoice_total=invoice.total_amount)

        if form.is_valid():
            invoice.mark_as_paid(
                payment_method   = form.cleaned_data['payment_method'],
                amount_received  = form.cleaned_data['amount_received'],
                payment_reference = form.cleaned_data.get('payment_reference', ''),
            )
            # Override paid_at with the form value if provided
            paid_at = form.cleaned_data.get('paid_at')
            if paid_at:
                Invoice.objects.filter(pk=invoice.pk).update(paid_at=paid_at)

            messages.success(
                request,
                f"✓ Payment recorded for {invoice.invoice_number}. Receipt is ready."
            )
            return redirect('core:receipt_detail', pk=invoice.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MarkAsPaidForm(invoice_total=invoice.total_amount)

    context = {
        'invoice': invoice,
        'form':    form,
    }
    return render(request, 'core/mark_as_paid.html', context)


def receipt_detail(request, pk):
    """
    Web view of a receipt (paid invoice). Not the PDF — the UI view.
    """
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk,
        status='paid'
    )
    business = BusinessProfile.get_profile()

    context = {
        'invoice':  invoice,
        'business': business,
    }
    return render(request, 'core/receipt_detail.html', context)


def invoice_cancel(request, pk):
    """Cancel a draft or sent invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status in ('paid',):
        messages.error(request, "A paid invoice cannot be cancelled.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        invoice.status = 'cancelled'
        invoice.save(update_fields=['status'])
        messages.success(request, f"Invoice {invoice.invoice_number} has been cancelled.")
        return redirect('core:invoice_list')

    return render(request, 'core/invoice_confirm_cancel.html', {'invoice': invoice})
```

---

## 3. URL Patterns (`core/urls.py` — add these)

```python
path('invoices/<int:pk>/pay/',     views.mark_as_paid,    name='mark_as_paid'),
path('invoices/<int:pk>/receipt/', views.receipt_detail,  name='receipt_detail'),
path('invoices/<int:pk>/cancel/',  views.invoice_cancel,  name='invoice_cancel'),
```

**Important:** There is a naming conflict — Wave 4 used `receipt_pdf` as the URL name for
PDF generation, and this wave introduces `receipt_detail` as the web view URL name.
Ensure these are distinct:
- `core:receipt_pdf`    → `/invoices/<pk>/receipt/pdf/` (PDF download)
- `core:receipt_detail` → `/invoices/<pk>/receipt/`     (web view)

Update Wave 4's PDF URL to:
```python
path('invoices/<int:pk>/receipt/pdf/', views.receipt_pdf, name='receipt_pdf'),
```

---

## 4. Templates

### `core/templates/core/mark_as_paid.html`

The payment form page. Must feel like a native mobile payment screen — clean, focused,
with a large CTA button. No clutter.

```html
{% extends 'base.html' %}
{% load widget_tweaks %}
{% block page_title %}Record Payment{% endblock %}

{% block extra_head %}
<style>
  .pay-field input,
  .pay-field select {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
    color: white;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
  }
  .pay-field input:focus, .pay-field select:focus {
    border-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16,185,129,0.15);
  }
  .pay-field label {
    display: block;
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 7px;
  }
  select option { background: #1e293b; }
</style>
{% endblock %}

{% block content %}
<div class="max-w-lg mx-auto space-y-5">

  <!-- Back + Title -->
  <div class="flex items-center gap-3">
    <a href="{% url 'core:invoice_detail' invoice.pk %}"
       class="p-2 rounded-xl bg-surface-800 border border-surface-700 hover:bg-surface-700 transition-colors">
      <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
    </a>
    <div>
      <h1 class="text-xl font-heading font-bold text-white">Record Payment</h1>
      <p class="text-xs text-slate-400 mt-0.5">{{ invoice.invoice_number }} · {{ invoice.client }}</p>
    </div>
  </div>

  <!-- Invoice Summary Card -->
  <div class="bg-surface-800 rounded-2xl border border-surface-700 p-5">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs text-slate-400 uppercase tracking-wider font-semibold">Amount Due</p>
        <p class="text-3xl font-heading font-extrabold text-white mt-1">
          ₦{{ invoice.total_amount|floatformat:2 }}
        </p>
      </div>
      <div class="text-right">
        <p class="text-xs text-slate-400">Due Date</p>
        <p class="text-sm font-semibold {% if invoice.is_overdue %}text-red-400{% else %}text-white{% endif %} mt-1">
          {{ invoice.due_date }}
        </p>
        {% if invoice.is_overdue %}
        <span class="text-xs text-red-400 font-semibold">OVERDUE</span>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Payment Form -->
  <form method="post">
    {% csrf_token %}
    <div class="bg-surface-800 rounded-2xl border border-surface-700 p-5 space-y-5">
      <h2 class="text-sm font-heading font-semibold text-white border-b border-surface-700 pb-3">
        Payment Details
      </h2>

      <!-- Amount Received -->
      <div class="pay-field">
        <label>Amount Received (₦)</label>
        {% render_field form.amount_received %}
        {% if form.amount_received.errors %}
        <p class="text-red-400 text-xs mt-1">{{ form.amount_received.errors|join:", " }}</p>
        {% endif %}
      </div>

      <!-- Payment Method -->
      <div class="pay-field">
        <label>Payment Method</label>
        {% render_field form.payment_method %}
        {% if form.payment_method.errors %}
        <p class="text-red-400 text-xs mt-1">{{ form.payment_method.errors|join:", " }}</p>
        {% endif %}
      </div>

      <!-- Payment Date & Time -->
      <div class="pay-field">
        <label>Payment Date & Time</label>
        {% render_field form.paid_at %}
        {% if form.paid_at.errors %}
        <p class="text-red-400 text-xs mt-1">{{ form.paid_at.errors|join:", " }}</p>
        {% endif %}
      </div>

      <!-- Payment Reference -->
      <div class="pay-field">
        <label>Reference / Transaction ID <span class="text-slate-500 normal-case">(optional)</span></label>
        {% render_field form.payment_reference %}
        {% if form.payment_reference.errors %}
        <p class="text-red-400 text-xs mt-1">{{ form.payment_reference.errors|join:", " }}</p>
        {% endif %}
      </div>

    </div>

    <!-- Submit -->
    <div class="mt-5 space-y-3">
      <button type="submit"
              class="w-full py-4 rounded-2xl bg-brand-500 hover:bg-brand-600 text-white text-base font-heading font-bold shadow-xl shadow-brand-500/40 transition-all active:scale-[0.98] flex items-center justify-center gap-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
        </svg>
        Confirm Payment
      </button>
      <a href="{% url 'core:invoice_detail' invoice.pk %}"
         class="block w-full py-3.5 rounded-2xl bg-surface-700 hover:bg-surface-600 text-slate-300 text-sm font-semibold text-center transition-colors">
        Cancel
      </a>
    </div>
  </form>

</div>
{% endblock %}
```

---

### `core/templates/core/receipt_detail.html`

The receipt web view — shown immediately after marking as paid, and accessible from the
invoice detail page. This is the digital receipt screen, designed to feel like a mobile
payment confirmation — think PayStack or Flutterwave success screen.

Build this template with:

**Layout structure:**
1. Large green ✓ success icon at top center
2. "Payment Received" heading
3. Receipt number and date
4. Payment summary card — amount, method, reference, date
5. Client name and invoice details card
6. Line items (collapsible on mobile, shown by default)
7. Totals block (subtotal, tax, total)
8. Two CTA buttons: **Download Receipt PDF** and **Back to Invoices**
9. Optional: **Resend Receipt** button (will be wired in Wave 7)

**Design requirements:**
- Top section should have a dark-to-green gradient or a prominent green glow effect
- The ✓ icon should be large (w-16 h-16) and animated (pulse or scale-in on load)
- Use `brand-500` (#10b981) as the hero color throughout
- Amount should be the largest text on screen (at least text-4xl)
- All cards should use `surface-800` background with `surface-700` border

**Example top section:**
```html
<!-- Success Hero -->
<div class="text-center py-8 px-4">
  <div class="w-20 h-20 rounded-full bg-brand-500/20 border-2 border-brand-500 flex items-center justify-center mx-auto mb-5 animate-bounce-once">
    <svg class="w-10 h-10 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
    </svg>
  </div>
  <h1 class="text-2xl font-heading font-extrabold text-white">Payment Received!</h1>
  <p class="text-slate-400 text-sm mt-2">{{ invoice.receipt_number }} · {{ invoice.paid_at|date:"d M Y, H:i" }}</p>
</div>
```

**CTA buttons:**
```html
<div class="space-y-3 mt-6">
  <a href="{% url 'core:receipt_pdf' invoice.pk %}"
     target="_blank"
     class="flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-brand-500 hover:bg-brand-600 text-white font-heading font-bold shadow-xl shadow-brand-500/40 transition-all active:scale-[0.98]">
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z"/>
    </svg>
    Download Receipt PDF
  </a>
  <a href="{% url 'core:invoice_list' %}"
     class="flex items-center justify-center gap-2 w-full py-3.5 rounded-2xl bg-surface-700 hover:bg-surface-600 text-slate-300 text-sm font-semibold transition-colors">
    Back to Invoices
  </a>
</div>
```

---

### `core/templates/core/invoice_confirm_cancel.html`

Simple confirmation page for cancelling an invoice.

```html
{% extends 'base.html' %}
{% block page_title %}Cancel Invoice{% endblock %}

{% block content %}
<div class="max-w-md mx-auto space-y-5">
  <div class="flex items-center gap-3">
    <a href="{% url 'core:invoice_detail' invoice.pk %}"
       class="p-2 rounded-xl bg-surface-800 border border-surface-700 hover:bg-surface-700 transition-colors">
      <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
    </a>
    <h1 class="text-xl font-heading font-bold text-white">Cancel Invoice</h1>
  </div>

  <div class="bg-surface-800 rounded-2xl border border-red-900/50 p-6 space-y-4">
    <div class="flex items-start gap-3">
      <div class="w-10 h-10 rounded-xl bg-red-900/50 flex items-center justify-center flex-shrink-0">
        <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
      </div>
      <div>
        <p class="text-sm font-semibold text-white">
          Cancel {{ invoice.invoice_number }}?
        </p>
        <p class="text-sm text-slate-400 mt-1">
          This will mark the invoice for <strong class="text-white">{{ invoice.client }}</strong>
          as cancelled. This action cannot be undone.
        </p>
      </div>
    </div>

    <form method="post" class="space-y-3">
      {% csrf_token %}
      <button type="submit"
              class="w-full py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold text-sm transition-colors">
        Yes, Cancel Invoice
      </button>
      <a href="{% url 'core:invoice_detail' invoice.pk %}"
         class="block w-full py-3 rounded-xl bg-surface-700 hover:bg-surface-600 text-slate-300 font-semibold text-sm text-center transition-colors">
        Keep Invoice
      </a>
    </form>
  </div>

</div>
{% endblock %}
```

---

## 5. Update Invoice Detail Template

In `core/templates/core/invoice_detail.html`, add the action buttons section.
Use this structure for the action buttons based on invoice status:

**For `draft` status:**
- Edit button
- Delete button (with confirmation link)
- Mark as Sent button (simple status update, no modal)
- Download Invoice PDF button

**For `sent` status:**
- Mark as Paid button → links to `mark_as_paid` view
- Edit button
- Download Invoice PDF button

**For `overdue` status:**
- Mark as Paid button (red/urgent styling) → links to `mark_as_paid` view
- Download Invoice PDF button

**For `paid` status:**
- View Receipt button → links to `receipt_detail`
- Download Receipt PDF button → links to `receipt_pdf`

**For `cancelled` status:**
- No action buttons, just a notice

Add a "Mark as Sent" view to update a draft invoice status to "sent":

```python
def mark_as_sent(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, status='draft')
    if request.method == 'POST':
        invoice.status = 'sent'
        invoice.save(update_fields=['status'])
        messages.success(request, f"{invoice.invoice_number} marked as sent.")
    return redirect('core:invoice_detail', pk=pk)
```

URL: `path('invoices/<int:pk>/sent/', views.mark_as_sent, name='mark_as_sent')`

---

## Acceptance Criteria

Before marking Wave 5 complete, verify ALL of the following:

- [ ] `GET /invoices/<pk>/pay/` shows the payment form pre-filled with invoice total
- [ ] Payment form pre-fills `amount_received` with `invoice.total_amount`
- [ ] Payment form pre-fills `paid_at` with current datetime (correctly formatted for datetime-local input)
- [ ] Submitting valid payment form transitions invoice status to `paid`
- [ ] After payment, user is redirected to receipt detail page
- [ ] Receipt detail page shows green ✓ success hero
- [ ] Receipt detail page shows payment amount, method, date, and reference
- [ ] Receipt detail page "Download Receipt PDF" button links to the PDF view
- [ ] Trying to pay an already-paid invoice redirects to detail with info message
- [ ] Cancelling an invoice from the confirmation page sets status to `cancelled`
- [ ] Paid invoice detail page shows receipt buttons, not edit/mark-as-paid buttons
- [ ] Draft invoice detail page shows "Edit", "Mark as Sent", "Download PDF" buttons
- [ ] Sent invoice detail page shows "Mark as Paid" as the primary action
- [ ] Mark as Sent updates invoice status from draft to sent
- [ ] All views are mobile-friendly at 390px viewport width

---

## Do NOT do in this wave
- Do not build email sending (Wave 7)
- Do not build settings page (Wave 6)
- Do not wire up "Resend Receipt" email button (Wave 7)
