import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts_app.models import User
from marketplace_app.api.review_serializers import (
    ReviewCreateSerializer,
    ReviewReadSerializer,
    ReviewUpdateSerializer,
)
from marketplace_app.models import Review


logger = logging.getLogger(__name__)
REVIEW_QUERY_PARAMETERS = {
    'business_user_id', 'reviewer_id', 'ordering',
}
REVIEW_ORDERING = {
    'updated_at': 'updated_at',
    '-updated_at': '-updated_at',
    'rating': 'rating',
    '-rating': '-rating',
}


class ReviewViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        try:
            reviews = self.filtered_reviews(request)
            data = ReviewReadSerializer(reviews, many=True).data
        except APIException:
            raise
        except Exception:
            logger.exception('Review list failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def filtered_reviews(self, request):
        unknown = set(request.query_params) - REVIEW_QUERY_PARAMETERS
        if unknown:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {'query': f'Unknown query parameter(s): {", ".join(sorted(unknown))}.'}
            )
        queryset = Review.objects.select_related('business_user', 'reviewer')
        for parameter, field in (
            ('business_user_id', 'business_user_id'),
            ('reviewer_id', 'reviewer_id'),
        ):
            if parameter in request.query_params:
                value = self.parse_id(parameter, request.query_params[parameter])
                queryset = queryset.filter(**{field: value})
        ordering = request.query_params.get('ordering', '-updated_at')
        if ordering not in REVIEW_ORDERING:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({'ordering': 'Unsupported ordering value.'})
        return queryset.order_by(REVIEW_ORDERING[ordering], 'pk')

    def parse_id(self, parameter, value):
        from rest_framework.exceptions import ValidationError

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({parameter: 'A valid integer is required.'}) from exc
        if parsed < 1:
            raise ValidationError({parameter: 'Value must be greater than zero.'})
        return parsed

    def create(self, request):
        if request.user.type != User.UserType.CUSTOMER:
            raise PermissionDenied('Only customer users may create reviews.')
        serializer = ReviewCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            review = serializer.save()
            data = ReviewReadSerializer(review).data
        except APIException:
            raise
        except Exception:
            logger.exception('Review creation failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        review = get_object_or_404(Review, pk=pk)
        if review.reviewer_id != request.user.pk:
            raise PermissionDenied('Only the review creator may update this review.')
        serializer = ReviewUpdateSerializer(
            data=request.data,
            context={'review': review},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        try:
            review = serializer.update_review()
            data = ReviewReadSerializer(review).data
        except APIException:
            raise
        except Exception:
            logger.exception('Review update failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(data)

    def destroy(self, request, pk=None):
        review = get_object_or_404(Review, pk=pk)
        if review.reviewer_id != request.user.pk:
            raise PermissionDenied('Only the review creator may delete this review.')
        try:
            review.delete()
        except Exception:
            logger.exception('Review deletion failed due to an internal error.')
            return Response(
                {'detail': 'Internal server error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
