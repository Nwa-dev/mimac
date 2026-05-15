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
          <p class="text-base font-heading font-bold text-white">₦{{ invoice.tot