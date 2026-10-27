import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from marketplace_app.api.pagination import OfferPagination
from marketplace_app.api.permissions import IsBusinessUser, IsOfferOwnerOrReadOnly
from marketplace_app.api.serializers import (
    OfferCreateSerializer,
    OfferCreateResponseSerializer,
    OfferDetailReadSerializer,
    OfferDetailReadOnlySerializer,
    OfferListSerializer,
    OfferUpdateSerializer,
    OfferUpdateResponseSerializer,
)
from marketplace_app.models import Offer, OfferDetail


logger = logging.getLogger(__name__)
OFFER_LIST_PARAMETERS = {
    'creator_id', 'min_price', 'max_delivery_time', 'ordering', 'search',
    'page_size', 'page',
}
OFFER_ORDERING_FIELDS = {
    'updated_at': 'updated_at',
    '-updated_at': '-updated_at',
    'min_price': 'min_price',
    '-min_price': '-min_price',
}


class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.all()
    pagination_class = OfferPagination
    permission_classes = (IsAuthenticated, IsOfferOwnerOrReadOnly)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_queryset(self):
        queryset = Offer.objects.select_related('user', 'user__profile').prefetch_related(
            'details',
        )
        if self.action != 'list':
            return queryset
        self.validate_list_query_parameters()
        params = self.request.query_params
        if 'creator_id' in params:
            creator_id = self.parse_positive_integer('creator_id')
            queryset = queryset.filter(user_id=creator_id)
        if 'min_price' in params:
            min_price = self.parse_decimal('min_price')
            minimum_price = OfferDetail.objects.filter(offer_id=OuterRef('pk')).order_by(
                'price'
            ).values('price')[:1]
            queryset = queryset.annotate(_minimum_price=Subquery(minimum_price)).filter(
                _minimum_price__gte=min_price
            )
        if 'max_delivery_time' in params:
            max_delivery_time = self.parse_positive_integer('max_delivery_time', allow_zero=True)
            queryset = queryset.filter(
                details__delivery_time_in_days__lte=max_delivery_time
            ).distinct()
        if 'search' in params:
            search_term = params['search']
            queryset = queryset.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
            )
        ordering = params.get('ordering', '-updated_at')
        if ordering not in OFFER_ORDERING_FIELDS:
            raise ValidationError({'ordering': 'Unsupported ordering value.'})
        ordering_field = OFFER_ORDERING_FIELDS[ordering]
        if ordering_field in {'min_price', '-min_price'}:
            minimum_price = OfferDetail.objects.filter(offer_id=OuterRef('pk')).order_by(
                'price'
            ).values('price')[:1]
            queryset = queryset.annotate(_minimum_price=Subquery(minimum_price))
            ordering_field = '_minimum_price' if ordering == 'min_price' else '-_minimum_price'
        return queryset.order_by(ordering_field, 'pk')

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated(), IsBusinessUser()]
        return [permission() for permission in self.permission_classes]

    def validate_list_query_parameters(self):
        unknown = set(self.request.query_params) - OFFER_LIST_PARAMETERS
        if unknown:
            raise ValidationError(
                {'query': f'Unknown query parameter(s): {", ".join(sorted(unknown))}.'}
            )
        for parameter in ('page', 'page_size'):
            if parameter in self.request.query_params:
                value = self.parse_positive_integer(parameter)
                if parameter == 'page_size' and value > 100:
                    continue

    def parse_positive_integer(self, name, allow_zero=False):
        try:
            value = int(self.request.query_params[name])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError({name: 'A valid integer is required.'}) from exc
        if value < 0 or (value == 0 and not allow_zero):
            raise ValidationError({name: 'Value is out of range.'})
        return value

    def parse_decimal(self, name):
        raw_value = self.request.query_params[name]
        try:
            value = Decimal(raw_value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({name: 'A valid decimal is required.'}) from exc
        if not value.is_finite() or value < 0:
            raise ValidationError({name: 'Value must be a non-negative decimal.'})
        if value.as_tuple().exponent < -2:
            raise ValidationError({name: 'At most two decimal places are allowed.'})
        return value

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = OfferListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            return Response(OfferListSerializer(queryset, many=True).data)
        except APIException:
            raise
        except Exception:
            logger.exception('Offer list failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        serializer = OfferCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            offer = serializer.save()
            response_data = OfferCreateResponseSerializer(
                offer, context={'request': request}
            ).data
        except APIException:
            raise
        except Exception:
            logger.exception('Offer creation failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(response_data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        offer = self.get_object()
        try:
            data = OfferDetailReadOnlySerializer(
                offer, context={'request': request}
            ).data
        except APIException:
            raise
        except Exception:
            logger.exception('Offer retrieval failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def partial_update(self, request, *args, **kwargs):
        offer = self.get_object()
        try:
            serializer = OfferUpdateSerializer(
                data=request.data,
                context={'offer': offer},
                partial=True,
            )
            serializer.is_valid(raise_exception=True)
            offer = serializer.update_offer()
            data = OfferUpdateResponseSerializer(
                offer, context={'request': request}
            ).data
        except APIException:
            raise
        except Exception:
            logger.exception('Offer update failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        offer = self.get_object()
        old_image = offer.image
        old_image_name = old_image.name if old_image else None
        try:
            offer.delete()
            if old_image_name:
                transaction.on_commit(
                    lambda: old_image.storage.delete(old_image_name), robust=True
                )
        except APIException:
            raise
        except Exception:
            logger.exception('Offer deletion failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OfferDetailViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, pk=None):
        detail = get_object_or_404(
            OfferDetail.objects.select_related('offer'),
            pk=pk,
        )
        try:
            data = OfferDetailReadSerializer(detail).data
        except APIException:
            raise
        except Exception:
            logger.exception('Offer detail retrieval failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)
