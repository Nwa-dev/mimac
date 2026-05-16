from django.utils import timezone


class OverdueCheckMiddleware:
    """
    Marks overdue invoices on every GET request.
    Throttled to once per 10 minutes via session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'GET' and not request.path.startswith('/admin/'):
            self._check_overdue(request)
        return self.get_response(request)

    def _check_overdue(self, request):
        last_check_key = '_overdue_checked_at'
        last_check = request.session.get(last_check_key)
        now_ts = timezone.now().timestamp()

        if last_check and (now_ts - last_check) < 600:
            return

        try:
            from core.models import Invoice
            Invoice.objects.filter(
                status__in=['sent', 'draft'],
                due_date__lt=timezone.now().date()
            ).update(status='overdue')
            request.session[last_check_key] = now_ts
        except Exception:
            pass
