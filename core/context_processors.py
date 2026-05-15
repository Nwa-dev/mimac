from .models import BusinessProfile


def business_profile(request):
    return {
        'business_profile': BusinessProfile.get_profile(),
    }
