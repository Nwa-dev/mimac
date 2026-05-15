from django.contrib import admin
from django.utils.html import format_html
from .models import BusinessProfile, Client, Invoice, InvoiceItem


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS PROFILE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Business Identity', {
            'fields': ('name', 'tagline', 'logo')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Tax & Banking', {
            'fields': ('tax_id', 'bank_name', 'account_name', 'account_number')
        }),
        ('PDF Notes', {
            'fields': ('invoice_footer_note', 'receipt_footer_note')
        }),
    )

    def has_add_permission(self, request):
        return not BusinessProfile.objects.exists()

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" height="50" />', obj.logo.url)
        return "No logo"
    logo_preview.short_description = 'Logo Preview'


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company_name', 'email', 'phone', 'city', 'created_at')
    list_filter   = ('city', 'state', 'country')
    search_fields = ('name', 'company_name', 'email', 'phone')
    ordering      = ('name',)
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'company_name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'country')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE ITEM INLINE
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceItemInline(admin.TabularInline):
    model  = InvoiceItem
    extra  = 1
    fields = ('description', 'quantity', 'unit_price', 'order')
    ordering = ('order',)


# ─────────────────────────────────────────────────────────────────────────────
# INVOICE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display   = ('invoice_number', 'client', 'issue_date', 'due_date', 'total_amount', 'colored_status', 'paid_at')
    list_filter    = ('status', 'issue_date', 'payment_method')
    search_fields  = ('invoice_number', 'client__name', 'client__company_name')
    ordering       = ('-created_at',)
    readonly_fields = ('invoice_number', 'subtotal', 'tax_amount', 'total_amount', 'created_at', 'updated_at')
    inlines        = [InvoiceItemInline]

    fieldsets = (
        ('Invoice', {
            'fields': ('invoice_number', 'client', 'issue_date', 'due_date', 'status', 'notes')
        }),
        ('Tax & Totals', {
            'fields': ('tax_rate', 'subtotal', 'tax_amount', 'total_amount')
        }),
        ('Payment Details', {
            'fields': ('paid_at', 'payment_method', 'amount_received', 'payment_reference'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def colored_status(self, obj):
        colors = {
            'draft':     '#94a3b8',
            'sent':      '#60a5fa',
            'paid':      '#34d399',
            'overdue':   '#f87171',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#94a3b8')
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display  = ('invoice', 'description', 'quantity', 'unit_price', 'line_total_display')
    search_fields = ('description', 'invoice__invoice_number')
    list_filter   = ('invoice__status',)

    def line_total_display(self, obj):
        return f"₦{obj.line_total:,.2f}"
    line_total_display.short_description = 'Line Total'


admin.site.site_header  = "Invoice System Admin"
admin.site.site_title   = "Invoice System"
admin.site.index_title  = "Management Panel"
