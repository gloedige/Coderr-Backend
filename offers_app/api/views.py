# Standard library
from decimal import Decimal, InvalidOperation

# Third-party
from django.db.models import OuterRef, Q, Subquery
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

# Local imports
from core.utils import handle_internal_errors, schedule_replaced_file_deletion
from offers_app.api.pagination import OfferPagination
from offers_app.api.permissions import IsBusinessUser, IsOfferOwnerOrReadOnly
from offers_app.api.serializers import (
    OfferCreateResponseSerializer,
    OfferCreateSerializer,
    OfferDetailReadOnlySerializer,
    OfferDetailReadSerializer,
    OfferListSerializer,
    OfferUpdateResponseSerializer,
    OfferUpdateSerializer,
)
from offers_app.models import Offer, OfferDetail


OFFER_LIST_PARAMETERS = {
    'creator_id', 'min_price', 'max_delivery_time', 'ordering', 'search',
    'page_size', 'page',
}
OFFER_ORDERINGS = {'updated_at', '-updated_at', 'min_price', '-min_price'}


def with_minimum_price(queryset):
    """Annotate offers with `_minimum_price` (lowest detail price) once."""
    if '_minimum_price' in queryset.query.annotations:
        return queryset
    lowest = OfferDetail.objects.filter(offer_id=OuterRef('pk')).order_by('price').values('price')[:1]
    return queryset.annotate(_minimum_price=Subquery(lowest))


class OfferViewSet(viewsets.ModelViewSet):
    """List, create, retrieve, update, and delete offers."""

    queryset = Offer.objects.all()
    pagination_class = OfferPagination
    permission_classes = (IsAuthenticated, IsOfferOwnerOrReadOnly)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self):
        """Return offers; for the list action also apply validated filters and ordering."""
        queryset = Offer.objects.select_related('user', 'user__profile').prefetch_related(
            'details',
        )
        if self.action != 'list':
            return queryset
        self.validate_list_query_parameters()
        return self.apply_ordering(self.apply_filters(queryset))

    def apply_filters(self, queryset):
        """Apply creator, minimum price, maximum delivery time, and search filters."""
        params = self.request.query_params
        if 'creator_id' in params:
            queryset = queryset.filter(user_id=self.parse_positive_integer('creator_id'))
        if 'min_price' in params:
            minimum = self.parse_decimal('min_price')
            queryset = with_minimum_price(queryset).filter(_minimum_price__gte=minimum)
        if 'max_delivery_time' in params:
            days = self.parse_positive_integer('max_delivery_time', allow_zero=True)
            queryset = queryset.filter(details__delivery_time_in_days__lte=days).distinct()
        if 'search' in params:
            term = params['search']
            queryset = queryset.filter(Q(title__icontains=term) | Q(description__icontains=term))
        return queryset

    def apply_ordering(self, queryset):
        """Order by the requested field (default newest first) with pk as tiebreaker."""
        ordering = self.request.query_params.get('ordering', '-updated_at')
        if ordering not in OFFER_ORDERINGS:
            raise ValidationError({'ordering': 'Unsupported ordering value.'})
        if ordering.lstrip('-') == 'min_price':
            queryset = with_minimum_price(queryset)
            ordering = ordering.replace('min_price', '_minimum_price')
        return queryset.order_by(ordering, 'pk')

    def get_permissions(self):
        """Return public access for list and business-only access for create."""
        if self.action == 'list':
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated(), IsBusinessUser()]
        return [permission() for permission in self.permission_classes]

    def validate_list_query_parameters(self):
        """Reject unknown query parameters and malformed page numbers or sizes."""
        params = self.request.query_params
        unknown = set(params) - OFFER_LIST_PARAMETERS
        if unknown:
            raise ValidationError(
                {'query': f'Unknown query parameter(s): {", ".join(sorted(unknown))}.'}
            )
        for parameter in ('page', 'page_size'):
            if parameter in params:
                self.parse_positive_integer(parameter)

    def parse_positive_integer(self, name, allow_zero=False):
        """Parse a non-negative (or positive) integer query parameter or raise 400."""
        try:
            value = int(self.request.query_params[name])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError({name: 'A valid integer is required.'}) from exc
        if value < 0 or (value == 0 and not allow_zero):
            raise ValidationError({name: 'Value is out of range.'})
        return value

    def parse_decimal(self, name):
        """Parse a non-negative decimal query parameter with at most two decimals."""
        try:
            value = Decimal(self.request.query_params[name])
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({name: 'A valid decimal is required.'}) from exc
        if not value.is_finite() or value < 0:
            raise ValidationError({name: 'Value must be a non-negative decimal.'})
        if value.as_tuple().exponent < -2:
            raise ValidationError({name: 'At most two decimal places are allowed.'})
        return value

    @handle_internal_errors('Offer list failed due to an internal error.')
    def list(self, request, *args, **kwargs):
        """Return the filtered, ordered, paginated offer list."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(OfferListSerializer(page, many=True).data)
        return Response(OfferListSerializer(queryset, many=True).data)

    def create(self, request, *args, **kwargs):
        """Validate the request and create an offer for the requesting business user."""
        serializer = OfferCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return self.save_offer(serializer, request)

    @handle_internal_errors('Offer creation failed due to an internal error.')
    def save_offer(self, serializer, request):
        """Persist the offer and return 201 with its data."""
        offer = serializer.save()
        data = OfferCreateResponseSerializer(offer, context={'request': request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Return a single offer with detail links."""
        return self.offer_response(request, self.get_object())

    @handle_internal_errors('Offer retrieval failed due to an internal error.')
    def offer_response(self, request, offer):
        """Serialize `offer` with detail links."""
        return Response(OfferDetailReadOnlySerializer(offer, context={'request': request}).data)

    def partial_update(self, request, *args, **kwargs):
        """Partially update an offer owned by the requester."""
        return self.update_response(request, self.get_object())

    @handle_internal_errors('Offer update failed due to an internal error.')
    def update_response(self, request, offer):
        """Validate and apply the update, then return the updated offer."""
        serializer = OfferUpdateSerializer(
            data=request.data, context={'offer': offer}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.update_offer()
        return Response(OfferUpdateResponseSerializer(offer, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        """Delete an offer owned by the requester and return 204."""
        return self.delete_offer(self.get_object())

    @handle_internal_errors('Offer deletion failed due to an internal error.')
    def delete_offer(self, offer):
        """Delete `offer`, schedule image removal, and return an empty 204 response."""
        old_image = offer.image
        offer.delete()
        schedule_replaced_file_deletion(old_image, None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OfferDetailView(generics.RetrieveAPIView):
    """Retrieve single offer details."""

    queryset = OfferDetail.objects.select_related('offer')
    serializer_class = OfferDetailReadSerializer
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        """Return the offer detail `pk` or 404."""
        return self.detail_response(self.get_object())

    @handle_internal_errors('Offer detail retrieval failed due to an internal error.')
    def detail_response(self, detail):
        """Serialize `detail`."""
        return Response(OfferDetailReadSerializer(detail).data)
