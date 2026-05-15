from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import Invoice, Client, BusinessProfile
from .forms import InvoiceForm, InvoiceItemFormSet, ClientForm, MarkAsPaidForm, BusinessProfileForm
from .utils.pdf import generate_pdf
from .utils.email_utils import send_invoice_email, send_receipt_email
from django.views.decorators.http import require_POST
import datetime


def dashboard(request):
    Invoice.objects.filter(
        status__in=['sent', 'draft'],
        due_date__lt=timezone.now().date()
    ).update(status='overdue')

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


def invoice_list(request):
    status_filter = request.GET.get('status', 'all')

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

    filter_tabs = [
        ('all',     'All',     counts['all']),
        ('draft',   'Draft',   counts['draft']),
        ('sent',    'Sent',    counts['sent']),
        ('paid',    'Paid',    counts['paid']),
        ('overdue', 'Overdue', counts['overdue']),
    ]

    context = {
        'invoices':      invoices,
        'status_filter': status_filter,
        'counts':        counts,
        'filter_tabs':   filter_tabs,
    }
    return render(request, 'core/invoice_list.html', context)


def invoice_create(request):
    if request.method == 'POST':
        form    = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST, prefix='items')

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
        formset = InvoiceItemFormSet(prefix='items')

    context = {
        'form':    form,
        'formset': formset,
        'title':   'New Invoice',
    }
    return render(request, 'core/invoice_form.html', context)


def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'), pk=pk
    )
    invoice.check_overdue()
    return render(request, 'core/invoice_detail.html', {'invoice': invoice})


def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.error(request, "A paid invoice cannot be edited.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        form    = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice, prefix='items')

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
        formset = InvoiceItemFormSet(instance=invoice, prefix='items')

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


@require_POST
def send_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.warning(request, "This invoice is already paid. Send the receipt instead.")
        return redirect('core:invoice_detail', pk=pk)

    if not invoice.client.email:
        messages.error(
            request,
            f"Client '{invoice.client}' has no email address. Add one via the client edit page."
        )
        return redirect('core:invoice_detail', pk=pk)

    success = send_invoice_email(invoice, request)

    if success:
        messages.success(
            request,
            f"Invoice {invoice.invoice_number} sent to {invoice.client.email}."
        )
    else:
        messages.error(request, "Failed to send email. Check your email settings or try again.")

    return redirect('core:invoice_detail', pk=pk)


@require_POST
def send_receipt(request, pk):
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
        messages.error(request, "Failed to send email. Check your email settings or try again.")

    return redirect('core:receipt_detail', pk=pk)


def settings_view(request):
    profile = BusinessProfile.objects.first()

    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            if request.POST.get('clear_logo') and profile and profile.logo:
                profile.logo.delete(save=False)
                instance = form.save(commit=False)
                instance.logo = None
                instance.save()
            else:
                form.save()
            messages.success(request, "Business profile updated successfully.")
            return redirect('core:settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BusinessProfileForm(instance=profile)

    return render(request, 'core/settings.html', {'form': form, 'profile': profile})


def mark_as_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

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
                payment_method=form.cleaned_data['payment_method'],
                amount_received=form.cleaned_data['amount_received'],
                payment_reference=form.cleaned_data.get('payment_reference', ''),
            )
            paid_at = form.cleaned_data.get('paid_at')
            if paid_at:
                Invoice.objects.filter(pk=invoice.pk).update(paid_at=paid_at)
            if invoice.client.email:
                sent = send_receipt_email(invoice)
                if sent:
                    messages.success(
                        request,
                        f"Payment recorded. Receipt emailed to {invoice.client.email}."
                    )
                else:
                    messages.success(
                        request,
                        "Payment recorded. Receipt is ready (email could not be sent — check settings)."
                    )
            else:
                messages.success(request, "Payment recorded. Receipt is ready.")
            return redirect('core:receipt_detail', pk=invoice.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = MarkAsPaidForm(invoice_total=invoice.total_amount)

    return render(request, 'core/mark_as_paid.html', {'invoice': invoice, 'form': form})


def receipt_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk,
        status='paid'
    )
    business = BusinessProfile.get_profile()
    return render(request, 'core/receipt_detail.html', {'invoice': invoice, 'business': business})


def invoice_cancel(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == 'paid':
        messages.error(request, "A paid invoice cannot be cancelled.")
        return redirect('core:invoice_detail', pk=pk)

    if request.method == 'POST':
        invoice.status = 'cancelled'
        invoice.save(update_fields=['status'])
        messages.success(request, f"Invoice {invoice.invoice_number} has been cancelled.")
        return redirect('core:invoice_list')

    return render(request, 'core/invoice_confirm_cancel.html', {'invoice': invoice})


def mark_as_sent(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, status='draft')
    if request.method == 'POST':
        invoice.status = 'sent'
        invoice.save(update_fields=['status'])
        messages.success(request, f"{invoice.invoice_number} marked as sent.")
    return redirect('core:invoice_detail', pk=pk)


def invoice_pdf(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk
    )
    business = BusinessProfile.get_profile()

    context = {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'INVOICE',
    }

    pdf_bytes = generate_pdf('core/pdf/invoice.html', context)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = request.GET.get('download', 'inline')
    filename = f"{invoice.invoice_number}.pdf"
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


def receipt_pdf(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('client').prefetch_related('items'),
        pk=pk,
        status='paid'
    )
    business = BusinessProfile.get_profile()

    context = {
        'invoice':       invoice,
        'business':      business,
        'document_type': 'RECEIPT',
    }

    pdf_bytes = generate_pdf('core/pdf/invoice.html', context)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    disposition = request.GET.get('download', 'inline')
    filename = f"{invoice.receipt_number}.pdf"
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


def client_list(request):
    query   = request.GET.get('q', '')
    clients = Client.objects.order_by('name')
    if query:
        clients = clients.filter(
            Q(name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query)
        )
    return render(request, 'core/client_list.html', {'clients': clients, 'query': query})


def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client '{client}' added successfully.")
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
    return render(request, 'core/client_detail.html', {'client': client, 'invoices': invoices})


def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Client '{client}' updated.")
            return redirect('core:client_detail', pk=client.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ClientForm(instance=client)
    return render(request, 'core/client_form.html', {
        'form': form, 'client': client, 'title': f'Edit {client}'
    })
