from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS PROFILE
# Single record. Feeds every invoice and receipt PDF.
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProfile(models.Model):
    name         = models.CharField(max_length=255, help_text="Full business name")
    tagline      = models.CharField(max_length=255, blank=True, help_text="Optional tagline shown on PDFs")
    logo         = models.ImageField(upload_to='business/', blank=True, null=True, help_text="Business logo (PNG or JPG recommended)")
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city         = models.CharField(max_length=100, blank=True)
    state        = models.CharField(max_length=100, blank=True)
    country      = models.CharField(max_length=100, default='Nigeria')
    postal_code  = models.CharField(max_length=20, blank=True)
    phone        = models.CharField(max_length=30, blank=True)
    email        = models.EmailField(blank=True)
    website      = models.URLField(blank=True)
    tax_id       = models.CharField(max_length=100, blank=True, help_text="RC number, TIN, or VAT ID")
    bank_name    = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    invoice_footer_note = models.TextField(
        blank=True,
        default='Thank you for your business.',
        help_text="Note printed at the bottom of every invoice"
    )
    receipt_footer_note = models.TextField(
        blank=True,
        default='Payment received. Thank you.',
        help_text="Note printed at the bottom of every receipt"
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Business Profile'
        verbose_name_plural = 'Business Profile'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Enforce single record — only one BusinessProfile can exist."""
        if not self.pk and BusinessProfile.objects.exists():
            raise ValueError("Only one BusinessProfile can exist. Edit the existing one.")
        super().save(*args, **kwargs)

    @classmethod
    def get_profile(cls):
        """Safe accessor — returns the profile or None."""
        return cls.objects.first()

    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.postal_code, self.country]
        return ', '.join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT
# A business or individual the invoice is billed to.
# ─────────────────────────────────────────────────────────────────────────────

class Client(models.Model):
    name           = models.CharField(max_length=255)
    email          = models.EmailField(blank=True)
    phone          = models.CharField(max_length=30, blank=True)
    address_line1  = models.CharField(max_length=255, blank=True)
    address_line2  = models.CharField(max_length=255, blank=True)
    city           = models.CharField(max_length=100, blank=True)
    state          = models.CharField(max_length=100, blank=True)
    country        = models.CharField(max_length=100, blank=True)
    company_name   = models.CharField(max_length=255, blank=True, help_text="Optional company name if different from contact name")
    notes          = models.TextField(blank=True, help_text="Internal notes about this client")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.company_name if self.company_name else self.name

    @property
    def display_name(self):
        if self.company_name:
            return f"{self.company_name} ({self.name})"
        return self.name

    @property
    def full_address(self):
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.country]
        return ', '.join(p for p in parts if p)

    @property
    def total_invoiced(self):
        return self.invoices.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')

    @property
    def total_paid(self):
        return self.invoices.filter(status='paid').aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')

    @property
    def outstanding_balance(self):
        return self.total_invoiced - self.total_paid


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE
# Central entity. Status drives the entire flow.
# ─────────────────────────────────────────────────────────────────────────────

class Invoice(models.Model):

    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('sent',     'Sent'),
        ('paid',     'Paid'),
        ('overdue',  'Overdue'),
        ('cancelled','Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash',          'Cash'),
        ('card',          'Card'),
        ('mobile_money',  'Mobile Money'),
        ('cheque',        'Cheque'),
        ('other',         'Other'),
    ]

    # Identity
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    client         = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='invoices')

    # Dates
    issue_date     = models.DateField(default=timezone.now)
    due_date       = models.DateField()

    # Financials (stored on model for quick querying — computed from items)
    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    tax_rate       = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax percentage e.g. 7.5 for 7.5% VAT"
    )
    tax_amount     = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    total_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)

    # Status
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Payment (populated when status → paid)
    paid_at        = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, blank=True)
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True, help_text="Transaction ID, cheque number, etc.")

    # Content
    notes          = models.TextField(blank=True, help_text="Additional notes shown on the invoice")

    # Metadata
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} — {self.client.name}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_invoice_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_invoice_number():
        """Generate sequential invoice number: INV-YYYYMM-XXXX"""
        now = timezone.now()
        prefix = f"INV-{now.year}{now.month:02d}-"
        last = Invoice.objects.filter(
            invoice_number__startswith=prefix
        ).order_by('invoice_number').last()
        if last:
            try:
                seq = int(last.invoice_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def recalculate_totals(self):
        """Recompute subtotal, tax, total from all line items. Call after saving items."""
        subtotal = sum(item.line_total for item in self.items.all())
        tax_amount = subtotal * (self.tax_rate / Decimal('100'))
        self.subtotal = subtotal
        self.tax_amount = tax_amount.quantize(Decimal('0.01'))
        self.total_amount = (subtotal + self.tax_amount).quantize(Decimal('0.01'))
        Invoice.objects.filter(pk=self.pk).update(
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
        )

    def mark_as_paid(self, payment_method, amount_received, payment_reference=''):
        """Transition invoice to paid state."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.payment_method = payment_method
        self.amount_received = amount_received
        self.payment_reference = payment_reference
        self.save()

    def check_overdue(self):
        """Mark as overdue if past due date and not paid."""
        if self.status in ('sent', 'draft') and self.due_date < timezone.now().date():
            self.status = 'overdue'
            self.save(update_fields=['status'])

    @property
    def is_paid(self):
        return self.status == 'paid'

    @property
    def is_overdue(self):
        return self.status == 'overdue' or (
            self.status in ('sent', 'draft') and self.due_date < timezone.now().date()
        )

    @property
    def balance_due(self):
        """Amount still outstanding."""
        if self.is_paid:
            return Decimal('0.00')
        return self.total_amount

    @property
    def receipt_number(self):
        """Receipt number derived from invoice number."""
        return self.invoice_number.replace('INV-', 'RCP-')

    @property
    def status_color(self):
        """Returns a Tailwind CSS color class for the status badge."""
        return {
            'draft':     'bg-slate-700 text-slate-300',
            'sent':      'bg-blue-900/50 text-blue-300',
            'paid':      'bg-emerald-900/50 text-emerald-300',
            'overdue':   'bg-red-900/50 text-red-300',
            'cancelled': 'bg-gray-800 text-gray-400',
        }.get(self.status, 'bg-slate-700 text-slate-300')

    @property
    def payment_method_display_label(self):
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method)


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE ITEM
# Line items on an invoice. Each item has qty × unit_price = line_total.
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.TextField(help_text="Service or product description")
    quantity    = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price  = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    order       = models.PositiveIntegerField(default=0, help_text="Display order of line items")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.description[:50]} — {self.quantity} × {self.unit_price}"

    @property
    def line_total(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.recalculate_totals()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate_totals()
