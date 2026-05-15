# WAVE 3 — Invoice CRUD & UI

## Context
You are building a Django Invoice & Receipt Management System for a small business.
Waves 1 and 2 are complete: project scaffold, settings, base template, and all models
with migrations. This is Wave 3. Build ONLY what is specified here.

The UI must be mobile-first, dark-themed (matching Wave 1 base template), and visually
polished. Every page should feel like a native mobile app, not a desktop form ported to mobile.

---

## Objectives
- Build all views, URLs, forms, and templates for:
  - Invoice list (dashboard overview)
  - Invoice detail
  - Invoice create (with dynamic line items)
  - Invoice edit
  - Client create
  - Client list
- Wire up all navigation links in `base.html`
- Update the dashboard with real summary stats

---

## 1. Forms (`core/forms.py`)

Create `core/forms.py`:

```python
from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem, Client, BusinessProfile


class ClientForm(forms.ModelForm):
    class Meta:
        model  = Client
        fields = [
            'name', 'company_name', 'email', 'phone',
            'address_line1', 'address_line2', 'city', 'state', 'country',
            'notes'
        ]
        widgets = {
            'name':          forms.TextInput(attrs={'placeholder': 'Full name'}),
            'company_name':  forms.TextInput(attrs={'placeholder': 'Company name (optional)'}),
            'email':         forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
            'phone':         forms.TextInput(attrs={'placeholder': '+234 800 000 0000'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street address'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Apt, suite, etc. (optional)'}),
            'city':          forms.TextInput(attrs={'placeholder': 'City'}),
            'state':         forms.TextInput(attrs={'placeholder': 'State'}),
            'country':       forms.TextInput(attrs={'placeholder': 'Country'}),
            'notes':         forms.Textarea(attrs={'placeholder': 'Internal notes...', 'rows': 3}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model  = Invoice
        fields = ['client', 'issue_date', 'due_date', 'tax_rate', 'notes']
        widgets = {
            'client':    forms.Select(),
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date':   forms.DateInput(attrs={'type': 'date'}),
            'tax_rate':   forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'notes':      forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes for the client...'}),
        }


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model  = InvoiceItem
        fields = ['description', 'quantity', 'unit_price', 'order']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Service or product description'}),
            'quantity':    forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '1'}),
            'unit_price':  forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'order':       forms.HiddenInput(),
        }


# Inline formset: Invoice → InvoiceItems
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    fields=['description', 'quantity', 'unit_price', 'order'],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
```

---

## 2. Views (`core/views.py`)

Replace the entire `core/views.py`:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from .models import Invoice, Client, BusinessProfile
from .forms import InvoiceForm, InvoiceItemFormSet, ClientForm
import datetime


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def dashboard(request):
    # Mark overdue invoices on every dashboard load
    overdue_candidates = Invoice.objects.filter(
        status__in=['sent', 'draft'],
        due_date__lt=timezone.now().date()
    )
    overdue_candidates.update(status='overdue')

    # Summary stats
    total_invoiced = Invoice.objects.exclude(
        status='cancelled'
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    total_paid = Invoice.objects.filter(
        status='paid'
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    total_outstanding = Invoice.objects.filter(
        status__in=['sent', 'overdue']
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    invoice_counts = Invoice.objects.aggregate(
        draft=Count('id', filter=Q(status='draft')),
        sent=Count('id', filter=Q(status='sent')),
        paid=Count('id', filter=Q(status='paid')),
        overdue=Count('id', filter=Q(status='overdue')),
    )

    # Recent invoices (last 10)
    recent_invoices = Invoice.objects.select_related('client').order_by('-created_at')[:10]

    context = {
        'total_invoiced':    total_invoiced,
        'total_paid':        total_paid,
        'total_outstanding': total_outstanding,
        'invoice_counts':    invoice_counts,
        'recent_invoices':   recent_invoices,
        'client_count':      Client.objects.count(),
    }
    return render(request, 'core/dashboard.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def invoice_list(request):
    status_filter = request.GET.get('status', 'all')

    # Mark overdue
    Invoice.objects.filter(
        status__in=['sent', 'draft'],
        due_date__lt=timezone.now().date()
    ).update(status='overdue')

    invoices = Invoice.objects.select_related('client').order_by('-created_at')

    if status_filter != 'all':
        invoices = invoices.filter(status=status_filter)

    counts = Invoice.objects.aggregate(
        all=Count('id'),
        draft=Count('id', filter=Q(status='draft')),
        sent=Count('id', filter=Q(status='sent')),
        paid=Count('id', filter=Q(status='paid')),
        overdue=Count('id', filter=Q(status='overdue')),
    )

    context = {
        'invoices':      invoices,
        'status_filter': status_filter,
        'counts':        counts,
    }
    return render(request, 'core/invoice_list.html', context)


def invoice_create(request):
    if request.method == 'POST':
        form    = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            invoice = form.save()
            formset.instance = invoice
            formset.save()
            invoice.recalculate_totals()
            messages.success(request, f"Invoice {invoice.invoice_number} created successfully.")
            return redirect('core:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form    = InvoiceForm(initial={
            'issue_date': timezone.now().date(),
            'due_date':   timezone.now().date() + datetime.timedelta(days=14),
        })
        formset = InvoiceItemFormSet()

    context = {
        'form':    form,
        'formset': formset,
        'title':   'New Invoice',
    }
    return render(request, 'core/invoice_form.html', context)


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related('client').prefetch_related('items'), pk=pk)
    invoice.check_overdue()
    context = {'invoice': invoice}
    return render(request, 'core/invoice_detail.html', context)


def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.error(request, "A paid invoice cannot be edited.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        form    = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            invoice.recalculate_totals()
            messages.success(request, f"Invoice {invoice.invoice_number} updated.")
            return redirect('core:invoice_detail', pk=invoice.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form    = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)

    context = {
        'form':    form,
        'formset': formset,
        'invoice': invoice,
        'title':   f'Edit {invoice.invoice_number}',
    }
    return render(request, 'core/invoice_form.html', context)


def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.error(request, "A paid invoice cannot be deleted.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f"Invoice {number} deleted.")
        return redirect('core:invoice_list')

    return render(request, 'core/invoice_confirm_delete.html', {'invoice': invoice})


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def client_list(request):
    query   = request.GET.get('q', '')
    clients = Client.objects.order_by('name')
    if query:
        clients = clients.filter(
            Q(name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query)
        )
    context = {
        'clients': clients,
        'query':   query,
    }
    return render(request, 'core/client_list.html', context)


def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client '{client}' added successfully.")
            # If came from invoice creation, redirect back
            next_url = request.GET.get('next', '')
            if next_url:
                return redirect(next_url)
            return redirect('core:client_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ClientForm()

    return render(request, 'core/client_form.html', {'form': form, 'title': 'New Client'})


def client_detail(request, pk):
    client   = get_object_or_404(Client, pk=pk)
    invoices = Invoice.objects.filter(client=client).order_by('-created_at')
    context  = {
        'client':   client,
        'invoices': invoices,
    }
    return render(request, 'core/client_detail.html', context)


def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Client '{client}' updated.")
            return redirect('core:client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(request, 'core/client_form.html', {'form': form, 'client': client, 'title': f'Edit {client}'})
```

---

## 3. URLs (`core/urls.py`)

```python
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Invoices
    path('invoices/',               views.invoice_list,   name='invoice_list'),
    path('invoices/new/',           views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/',      views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit,   name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),

    # Clients
    path('clients/',               views.client_list,   name='client_list'),
    path('clients/new/',           views.client_create, name='client_create'),
    path('clients/<int:pk>/',      views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit,   name='client_edit'),
]
```

---

## 4. Templates

### `core/templates/core/dashboard.html`

Real dashboard with stats cards and recent invoices table.

```html
{% extends 'base.html' %}
{% block page_title %}Dashboard{% endblock %}

{% block content %}
<div class="space-y-6">

  <!-- Page Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-heading font-bold text-white">Dashboard</h1>
      <p class="text-slate-400 text-sm mt-1">Overview of your invoices</p>
    </div>
    <a href="{% url 'core:invoice_create' %}"
       class="hidden sm:flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-brand-500/30 active:scale-95">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
      </svg>
      New Invoice
    </a>
  </div>

  <!-- Stats Grid -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">

    <div class="bg-surface-800 rounded-2xl p-4 border border-surface-700">
      <p class="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Invoiced</p>
      <p class="text-xl font-heading font-bold text-white mt-2">₦{{ total_invoiced|floatformat:0 }}</p>
      <p class="text-xs text-slate-500 mt-1">All time</p>
    </div>

    <div class="bg-surface-800 rounded-2xl p-4 border border-surface-700">
      <p class="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Paid</p>
      <p class="text-xl font-heading font-bold text-brand-400 mt-2">₦{{ total_paid|floatformat:0 }}</p>
      <p class="text-xs text-slate-500 mt-1">{{ invoice_counts.paid }} invoice{{ invoice_counts.paid|pluralize }}</p>
    </div>

    <div class="bg-surface-800 rounded-2xl p-4 border border-surface-700">
      <p class="text-xs text-slate-400 font-medium uppercase tracking-wider">Outstanding</p>
      <p class="text-xl font-heading font-bold text-yellow-400 mt-2">₦{{ total_outstanding|floatformat:0 }}</p>
      <p class="text-xs text-slate-500 mt-1">{{ invoice_counts.sent }} sent</p>
    </div>

    <div class="bg-surface-800 rounded-2xl p-4 border border-surface-700">
      <p class="text-xs text-slate-400 font-medium uppercase tracking-wider">Overdue</p>
      <p class="text-xl font-heading font-bold text-red-400 mt-2">{{ invoice_counts.overdue }}</p>
      <p class="text-xs text-slate-500 mt-1">Need attention</p>
    </div>

  </div>

  <!-- Recent Invoices -->
  <div class="bg-surface-800 rounded-2xl border border-surface-700 overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4 border-b border-surface-700">
      <h2 class="text-sm font-heading font-semibold text-white">Recent Invoices</h2>
      <a href="{% url 'core:invoice_list' %}" class="text-xs text-brand-400 hover:text-brand-300 font-medium">View all →</a>
    </div>

    {% if recent_invoices %}
    <div class="divide-y divide-surface-700">
      {% for invoice in recent_invoices %}
      <a href="{% url 'core:invoice_detail' invoice.pk %}"
         class="flex items-center justify-between px-5 py-4 hover:bg-surface-700/50 transition-colors duration-150">
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-white truncate">{{ invoice.client }}</p>
          <p class="text-xs text-slate-400 mt-0.5">{{ invoice.invoice_number }} · Due {{ invoice.due_date }}</p>
        </div>
        <div class="flex items-center gap-3 ml-4">
          <span class="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-semibold {{ invoice.status_color }}">
            {{ invoice.get_status_display }}
          </span>
          <p class="text-sm font-bold text-white whitespace-nowrap">₦{{ invoice.total_amount|floatformat:0 }}</p>
        </div>
      </a>
      {% endfor %}
    </div>
    {% else %}
    <div class="px-5 py-12 text-center">
      <div class="w-12 h-12 rounded-2xl bg-surface-700 flex items-center justify-center mx-auto mb-4">
        <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <p class="text-sm font-semibold text-white">No invoices yet</p>
      <p class="text-xs text-slate-400 mt-1">Create your first invoice to get started</p>
      <a href="{% url 'core:invoice_create' %}"
         class="inline-flex items-center gap-2 mt-4 bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200">
        Create Invoice
      </a>
    </div>
    {% endif %}
  </div>

</div>
{% endblock %}
```

---

### `core/templates/core/invoice_list.html`

```html
{% extends 'base.html' %}
{% block page_title %}Invoices{% endblock %}

{% block content %}
<div class="space-y-5">

  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-heading font-bold text-white">Invoices</h1>
    <a href="{% url 'core:invoice_create' %}"
       class="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-brand-500/30 active:scale-95">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
      </svg>
      <span class="hidden sm:inline">New Invoice</span>
    </a>
  </div>

  <!-- Status Filter Tabs -->
  <div class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
    {% for tab_status, tab_label, tab_count in filter_tabs %}
    <a href="?status={{ tab_status }}"
       class="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-200
              {% if status_filter == tab_status %}bg-brand-500 text-white{% else %}bg-surface-800 text-slate-400 hover:text-white border border-surface-700{% endif %}">
      {{ tab_label }}
      <span class="{% if status_filter == tab_status %}bg-white/20{% else %}bg-surface-700{% endif %} rounded-md px-1.5 py-0.5">
        {{ tab_count }}
      </span>
    </a>
    {% endfor %}
  </div>

  <!-- Invoice Cards -->
  {% if invoices %}
  <div class="space-y-3">
    {% for invoice in invoices %}
    <a href="{% url 'core:invoice_detail' invoice.pk %}"
       class="block bg-surface-800 rounded-2xl border border-surface-700 p-4 hover:border-brand-500/40 transition-all duration-200 active:scale-[0.99]">
      <div class="flex items-start justify-between gap-3">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <p class="text-sm font-bold text-white truncate">{{ invoice.client }}</p>
          </div>
          <p class="text-xs text-slate-400 mt-1">{{ invoice.invoice_number }}</p>
          <p class="text-xs text-slate-500 mt-1">
            Issued: {{ invoice.issue_date }} · Due: {{ invoice.due_date }}
          </p>
        </div>
        <div class="text-right flex-shrink-0">
          <p class="text-base font-heading font-bold text-white">₦{{ invoice.total_amount|floatformat:0 }}</p>
          <span class="inline-flex mt-1.5 items-center px-2 py-0.5 rounded-lg text-xs font-semibold {{ invoice.status_color }}">
            {{ invoice.get_status_display }}
          </span>
        </div>
      </div>
    </a>
    {% endfor %}
  </div>
  {% else %}
  <!-- Empty State -->
  <div class="bg-surface-800 rounded-2xl border border-surface-700 px-6 py-16 text-center">
    <div class="w-14 h-14 rounded-2xl bg-surface-700 flex items-center justify-center mx-auto mb-4">
      <svg class="w-7 h-7 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.414V19a2 2 0 01-2 2z"/>
      </svg>
    </div>
    <p class="text-sm font-semibold text-white">No invoices found</p>
    <p class="text-xs text-slate-400 mt-1">
      {% if status_filter != 'all' %}No {{ status_filter }} invoices.{% else %}Create your first invoice.{% endif %}
    </p>
    {% if status_filter == 'all' %}
    <a href="{% url 'core:invoice_create' %}"
       class="inline-flex items-center gap-2 mt-5 bg-brand-500 hover:bg-brand-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all">
      + New Invoice
    </a>
    {% endif %}
  </div>
  {% endif %}

</div>
{% endblock %}

{% block extra_scripts %}
<script>
  // Build filter tabs dynamically from counts data passed via template
  // (tabs are rendered server-side above; no JS needed)
</script>
{% endblock %}
```

**Note for Claude Code:** The `filter_tabs` context variable must be added to the `invoice_list` view:

```python
# Add to invoice_list view, inside context dict:
'filter_tabs': [
    ('all',     'All',     counts['all']),
    ('draft',   'Draft',   counts['draft']),
    ('sent',    'Sent',    counts['sent']),
    ('paid',    'Paid',    counts['paid']),
    ('overdue', 'Overdue', counts['overdue']),
],
```

---

### `core/templates/core/invoice_form.html`

Create/Edit invoice form with dynamic line items. The form must support adding and removing
line items without a page reload (use vanilla JavaScript).

```html
{% extends 'base.html' %}
{% load widget_tweaks %}
{% block page_title %}{{ title }}{% endblock %}

{% block extra_head %}
<style>
  .form-field input, .form-field select, .form-field textarea {
    width: 100%;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px 14px;
    color: white;
    font-size: 14px;
    transition: border-color 0.2s;
    outline: none;
  }
  .form-field input:focus, .form-field select:focus, .form-field textarea:focus {
    border-color: #10b981;
  }
  .form-field label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  select option { background: #1e293b; }
</style>
{% endblock %}

{% block content %}
<form method="post" id="invoice-form">
  {% csrf_token %}
  {{ formset.management_form }}

  <div class="space-y-6">

    <!-- Back + Title -->
    <div class="flex items-center gap-3">
      <a href="{% url 'core:invoice_list' %}" class="p-2 rounded-xl bg-surface-800 border border-surface-700 hover:bg-surface-700 transition-colors">
        <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
      </a>
      <h1 class="text-xl font-heading font-bold text-white">{{ title }}</h1>
    </div>

    <!-- Client & Dates -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 p-5 space-y-4">
      <h2 class="text-sm font-heading font-semibold text-white border-b border-surface-700 pb-3">Invoice Details</h2>

      <div class="form-field">
        <label for="{{ form.client.id_for_label }}">Client</label>
        {% render_field form.client %}
        {% if form.client.errors %}
        <p class="text-red-400 text-xs mt-1">{{ form.client.errors|join:", " }}</p>
        {% endif %}
      </div>

      <div class="flex items-center justify-between text-xs text-slate-400">
        <span>Client not listed?</span>
        <a href="{% url 'core:client_create' %}?next={% url 'core:invoice_create' %}"
           class="text-brand-400 hover:text-brand-300 font-medium">+ Add new client</a>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div class="form-field">
          <label for="{{ form.issue_date.id_for_label }}">Issue Date</label>
          {% render_field form.issue_date %}
        </div>
        <div class="form-field">
          <label for="{{ form.due_date.id_for_label }}">Due Date</label>
          {% render_field form.due_date %}
        </div>
      </div>

      <div class="form-field">
        <label for="{{ form.tax_rate.id_for_label }}">Tax Rate (%)</label>
        {% render_field form.tax_rate %}
      </div>

      <div class="form-field">
        <label for="{{ form.notes.id_for_label }}">Notes (optional)</label>
        {% render_field form.notes %}
      </div>
    </div>

    <!-- Line Items -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 p-5 space-y-4">
      <div class="flex items-center justify-between border-b border-surface-700 pb-3">
        <h2 class="text-sm font-heading font-semibold text-white">Line Items</h2>
        <button type="button" id="add-item-btn"
                class="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-semibold transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
          </svg>
          Add Item
        </button>
      </div>

      <!-- Formset Container -->
      <div id="formset-container" class="space-y-4">
        {% for item_form in formset %}
        <div class="item-row bg-surface-700/50 rounded-xl p-4 space-y-3 relative">
          {{ item_form.id }}
          {{ item_form.order }}

          <!-- DELETE checkbox (hidden, triggered by remove button) -->
          <div class="hidden">{{ item_form.DELETE }}</div>

          <div class="form-field">
            <label>Description</label>
            {% render_field item_form.description %}
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="form-field">
              <label>Qty</label>
              {% render_field item_form.quantity class="item-qty" %}
            </div>
            <div class="form-field">
              <label>Unit Price (₦)</label>
              {% render_field item_form.unit_price class="item-price" %}
            </div>
          </div>

          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-400">
              Line total: <span class="text-white font-semibold item-line-total">₦0.00</span>
            </p>
            <button type="button" class="remove-item-btn text-xs text-red-400 hover:text-red-300 font-medium transition-colors">
              Remove
            </button>
          </div>
        </div>
        {% endfor %}
      </div>

      <!-- Empty item row template (cloned by JS) -->
      <template id="item-template">
        <div class="item-row bg-surface-700/50 rounded-xl p-4 space-y-3 relative">
          <input type="hidden" name="items-__prefix__-id" />
          <input type="hidden" name="items-__prefix__-order" value="__prefix__" />
          <input type="hidden" name="items-__prefix__-DELETE" class="delete-checkbox" />
          <div class="form-field">
            <label>Description</label>
            <input type="text" name="items-__prefix__-description" placeholder="Service or product description" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-field">
              <label>Qty</label>
              <input type="number" name="items-__prefix__-quantity" class="item-qty" step="0.01" min="0.01" placeholder="1" value="1" />
            </div>
            <div class="form-field">
              <label>Unit Price (₦)</label>
              <input type="number" name="items-__prefix__-unit_price" class="item-price" step="0.01" min="0" placeholder="0.00" />
            </div>
          </div>
          <div class="flex items-center justify-between">
            <p class="text-xs text-slate-400">Line total: <span class="text-white font-semibold item-line-total">₦0.00</span></p>
            <button type="button" class="remove-item-btn text-xs text-red-400 hover:text-red-300 font-medium">Remove</button>
          </div>
        </div>
      </template>

    </div>

    <!-- Totals Summary -->
    <div class="bg-surface-800 rounded-2xl border border-surface-700 p-5 space-y-3">
      <h2 class="text-sm font-heading font-semibold text-white border-b border-surface-700 pb-3">Summary</h2>
      <div class="space-y-2 text-sm">
        <div class="flex justify-between text-slate-400">
          <span>Subtotal</span>
          <span id="summary-subtotal" class="text-white font-medium">₦0.00</span>
        </div>
        <div class="flex justify-between text-slate-400">
          <span>Tax (<span id="tax-rate-display">0</span>%)</span>
          <span id="summary-tax" class="text-white font-medium">₦0.00</span>
        </div>
        <div class="flex justify-between font-heading font-bold text-white text-base border-t border-surface-700 pt-2 mt-2">
          <span>Total</span>
          <span id="summary-total">₦0.00</span>
        </div>
      </div>
    </div>

    <!-- Submit Buttons -->
    <div class="flex gap-3 pb-4">
      <a href="{% url 'core:invoice_list' %}"
         class="flex-1 text-center py-3 rounded-xl bg-surface-700 text-slate-300 text-sm font-semibold hover:bg-surface-600 transition-colors">
        Cancel
      </a>
      <button type="submit"
              class="flex-1 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold shadow-lg shadow-brand-500/30 transition-all active:scale-95">
        {% if invoice %}Update Invoice{% else %}Create Invoice{% endif %}
      </button>
    </div>

  </div>
</form>
{% endblock %}

{% block extra_scripts %}
<script>
  const totalFormsInput = document.querySelector('[name="items-TOTAL_FORMS"]');
  const formsetContainer = document.getElementById('formset-container');
  const addBtn = document.getElementById('add-item-btn');
  const taxRateInput = document.querySelector('[name="tax_rate"]');
  const taxRateDisplay = document.getElementById('tax-rate-display');

  function formatCurrency(val) {
    return '₦' + parseFloat(val || 0).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function recalcTotals() {
    let subtotal = 0;
    document.querySelectorAll('.item-row').forEach(row => {
      const deleteBox = row.querySelector('.delete-checkbox');
      if (deleteBox && deleteBox.value === 'on') return; // skip deleted
      const qty   = parseFloat(row.querySelector('.item-qty')?.value  || 0);
      const price = parseFloat(row.querySelector('.item-price')?.value || 0);
      const lineTotal = qty * price;
      const lineTotalEl = row.querySelector('.item-line-total');
      if (lineTotalEl) lineTotalEl.textContent = formatCurrency(lineTotal);
      subtotal += lineTotal;
    });
    const taxRate = parseFloat(taxRateInput?.value || 0);
    const tax     = subtotal * (taxRate / 100);
    const total   = subtotal + tax;
    taxRateDisplay.textContent = taxRate;
    document.getElementById('summary-subtotal').textContent = formatCurrency(subtotal);
    document.getElementById('summary-tax').textContent      = formatCurrency(tax);
    document.getElementById('summary-total').textContent    = formatCurrency(total);
  }

  // Add new item row
  addBtn.addEventListener('click', () => {
    const idx      = parseInt(totalFormsInput.value);
    const template = document.getElementById('item-template').innerHTML
      .replace(/__prefix__/g, idx);
    const tmp = document.createElement('div');
    tmp.innerHTML = template;
    const newRow = tmp.firstElementChild;
    formsetContainer.appendChild(newRow);
    totalFormsInput.value = idx + 1;
    attachRowListeners(newRow);
    recalcTotals();
  });

  function attachRowListeners(row) {
    row.querySelector('.remove-item-btn')?.addEventListener('click', () => {
      const deleteBox = row.querySelector('.delete-checkbox');
      if (deleteBox) {
        deleteBox.value = 'on';
        row.style.display = 'none';
      } else {
        row.remove();
      }
      recalcTotals();
    });
    row.querySelector('.item-qty')?.addEventListener('input', recalcTotals);
    row.querySelector('.item-price')?.addEventListener('input', recalcTotals);
  }

  // Attach to existing rows
  document.querySelectorAll('.item-row').forEach(attachRowListeners);
  taxRateInput?.addEventListener('input', recalcTotals);

  // Initial calc on page load
  recalcTotals();
</script>
{% endblock %}
```

---

### `core/templates/core/invoice_detail.html`

Full invoice detail view — action buttons, line items table, payment summary.

Build this template with:
- Back button to invoice list
- Invoice number, client info, status badge prominent at top
- Line items listed clearly with subtotal, tax, total
- If status is `draft` or `sent`: show **Edit**, **Mark as Paid**, **Download PDF**, **Send** buttons
- If status is `paid`: show **Download Receipt**, **Resend Receipt** buttons and a green "PAID" payment block showing date, method, amount received
- If status is `overdue`: highlight due date in red, show "Mark as Paid" urgently

---

### `core/templates/core/client_list.html`

- Search bar at top
- Client cards showing name, company, email, phone, invoice count
- Empty state if no clients
- FAB/button to add new client

---

### `core/templates/core/client_form.html`

- Clean form using same field styling as `invoice_form.html`
- All `ClientForm` fields rendered with labels
- Cancel + Save buttons

---

### `core/templates/core/client_detail.html`

- Client header card (name, company, phone, email, address)
- Stats: Total Invoiced, Total Paid, Outstanding
- List of all invoices for this client (same card style as invoice_list)
- Edit client button

---

### `core/templates/core/invoice_confirm_delete.html`

- Simple confirmation page
- "Are you sure you want to delete Invoice X?" warning
- Cancel (goes back) and Delete (submits POST) buttons

---

## 5. Update `base.html` Navigation Links

Update all `href="#"` navigation links in `base.html` (both sidebar and bottom nav) to use
real URL tags:

- Dashboard → `{% url 'core:dashboard' %}`
- Invoices → `{% url 'core:invoice_list' %}`
- New Invoice FAB (bottom nav center button) → `{% url 'core:invoice_create' %}`
- Clients → `{% url 'core:client_list' %}`
- Settings → `{% url 'core:settings' %}` (will be built in Wave 6, leave as `#` for now)

Also add active state detection to bottom nav items using
`request.resolver_match.url_name` checks, just like the sidebar already does.

---

## Acceptance Criteria

Before marking Wave 3 complete, verify ALL of the following:

- [ ] `http://127.0.0.1:8000/` shows the dashboard with stat cards
- [ ] `http://127.0.0.1:8000/invoices/` shows the invoice list with status filter tabs
- [ ] `http://127.0.0.1:8000/invoices/new/` shows the invoice form
- [ ] Adding line items on the create form works without page reload
- [ ] Line total, subtotal, tax, and total all update live as user types
- [ ] Removing a line item recalculates totals instantly
- [ ] Submitting the form creates the invoice and redirects to detail page
- [ ] Invoice detail page shows all invoice data correctly
- [ ] Editing an invoice pre-fills all fields including existing line items
- [ ] Paid invoices cannot be edited (redirect with error message)
- [ ] `http://127.0.0.1:8000/clients/` shows the client list
- [ ] `http://127.0.0.1:8000/clients/new/` creates a new client
- [ ] All navigation links in sidebar and bottom nav are working
- [ ] Active nav item highlights correctly on each page
- [ ] All pages are usable on a 390px mobile viewport

---

## Do NOT do in this wave
- Do not build PDF download views (Wave 4)
- Do not build Mark as Paid functionality (Wave 5)
- Do not build email sending (Wave 7)
- Do not build the Settings page (Wave 6)
