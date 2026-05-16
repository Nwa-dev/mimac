from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def active_if(context, *url_names):
    """
    Returns 'active' if the current URL name matches any of the given names.
    Usage: {% active_if 'invoice_list' 'invoice_detail' %}
    """
    request = context.get('request')
    if not request:
        return ''
    current = request.resolver_match.url_name if request.resolver_match else ''
    return 'active' if current in url_names else ''


@register.filter
def currency(value):
    """Format a number as Nigerian Naira."""
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₦0.00"


@register.filter
def percentage(value):
    """Format a number as a percentage."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0%"
