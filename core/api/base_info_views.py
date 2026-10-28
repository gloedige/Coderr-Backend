from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts_app.models import Profile, User
from core.api.utils import internal_error_response
from marketplace_app.models import Offer, Review


def base_info_data():
    """Return public platform counts and a one-decimal average review rating."""
    review_count = Review.objects.count()
    average = Review.objects.aggregate(value=Avg('rating'))['value']
    rounded_average = Decimal(str(average or 0)).quantize(
        Decimal('0.1'), rounding=ROUND_HALF_UP
    )
    return {
        'review_count': review_count,
        'average_rating': float(rounded_average),
        'business_profile_count': Profile.objects.filter(
            user__type=User.UserType.BUSINESS
        ).count(),
        'offer_count': Offer.objects.count(),
    }


class BaseInfoView(APIView):
    """Expose public aggregate information about the platform."""

    permission_classes = (AllowAny,)

    def get(self, request):
        """Return platform aggregates or a generic response for unexpected failures."""
        try:
            data = base_info_data()
        except Exception:
            return internal_error_response('Base information request failed internally.')
        return Response(data)
