import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auth_app.models import User
from reviews_app.api.serializers import (
    ReviewCreateSerializer,
    ReviewReadSerializer,
    ReviewUpdateSerializer,
)
from reviews_app.models import Review


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


def internal_error(message):
    """Log an unexpected review API failure and return the standard safe response."""
    logger.exception(message)
    return Response(
        {'detail': 'Internal server error.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class ReviewViewSet(viewsets.ViewSet):
    """Expose authenticated review list/create/update/delete API operations."""

    lookup_value_regex = r'\d+'
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        """Return filtered, ordered review data for the authenticated requester."""
        try:
            reviews = self.filtered_reviews(request)
            data = ReviewReadSerializer(reviews, many=True).data
        except APIException:
            raise
        except Exception:
            return internal_error('Review list failed due to an internal error.')
        return Response(data)

    def filtered_reviews(self, request):
        """Build a validated review queryset from request filters and ordering."""
        self.validate_query_parameters(request)
        queryset = Review.objects.select_related('business_user', 'reviewer')
        queryset = self.apply_filters(queryset, request)
        return self.apply_ordering(queryset, request)

    def validate_query_parameters(self, request):
        """Validate allowed query keys and ordering values, raising a field error."""
        self.reject_unknown_parameters(request)
        ordering = request.query_params.get('ordering', '-updated_at')
        if ordering not in REVIEW_ORDERING:
            raise ValidationError({'ordering': 'Unsupported ordering value.'})

    def reject_unknown_parameters(self, request):
        """Reject undocumented query keys from the request query parameters."""
        unknown = set(request.query_params) - REVIEW_QUERY_PARAMETERS
        if unknown:
            raise ValidationError(
                {'query': f'Unknown query parameter(s): {", ".join(sorted(unknown))}.'}
            )

    def apply_filters(self, queryset, request):
        """Apply optional business-user and reviewer integer filters to a queryset."""
        for parameter in ('business_user_id', 'reviewer_id'):
            value = request.query_params.get(parameter)
            if value is not None:
                queryset = queryset.filter(**{parameter: self.parse_id(parameter, value)})
        return queryset

    def apply_ordering(self, queryset, request):
        """Order reviews by an allowed field and primary key for stable results."""
        ordering = request.query_params.get('ordering', '-updated_at')
        return queryset.order_by(REVIEW_ORDERING[ordering], 'pk')

    def parse_id(self, parameter, value):
        """Parse a positive integer query value or raise a parameter validation error."""
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({parameter: 'A valid integer is required.'}) from exc
        if parsed < 1:
            raise ValidationError({parameter: 'Value must be greater than zero.'})
        return parsed

    def create(self, request):
        """Create a review from request data after enforcing customer role and eligibility."""
        self.require_customer(request)
        serializer = self.review_create_serializer(request)
        return self.save_review(serializer)

    def require_customer(self, request):
        """Reject authenticated non-customer users from review creation."""
        if request.user.type != User.UserType.CUSTOMER:
            raise PermissionDenied('Only customer users may create reviews.')

    def review_create_serializer(self, request):
        """Validate request data and return a ready-to-save review serializer."""
        serializer = ReviewCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return serializer

    def save_review(self, serializer):
        """Persist the review and return 201 data or a sanitized 500 response."""
        try:
            review = serializer.save()
            data = ReviewReadSerializer(review).data
        except APIException:
            raise
        except Exception:
            return internal_error('Review creation failed due to an internal error.')
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """Partially update a review identified by ID when requested by its creator."""
        review = get_object_or_404(Review, pk=pk)
        self.require_review_creator(request, review)
        serializer = self.review_update_serializer(request, review)
        return self.save_review_update(serializer)

    def require_review_creator(self, request, review):
        """Verify the requester owns the review before a mutation."""
        if review.reviewer_id != request.user.pk:
            raise PermissionDenied('Only the review creator may modify this review.')

    def review_update_serializer(self, request, review):
        """Validate partial request fields against the supplied review instance."""
        serializer = ReviewUpdateSerializer(
            data=request.data,
            context={'review': review},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return serializer

    def save_review_update(self, serializer):
        """Persist validated changes and serialize the updated review response."""
        try:
            review = serializer.update_review()
            data = ReviewReadSerializer(review).data
        except APIException:
            raise
        except Exception:
            return internal_error('Review update failed due to an internal error.')
        return Response(data)

    def destroy(self, request, pk=None):
        """Delete the identified review if owned by the requester, returning 204."""
        review = get_object_or_404(Review, pk=pk)
        self.require_review_creator(request, review)
        return self.delete_review(review)

    def delete_review(self, review):
        """Delete a review and return 204 or a sanitized internal-error response."""
        try:
            review.delete()
        except Exception:
            return internal_error('Review deletion failed due to an internal error.')
        return Response(status=status.HTTP_204_NO_CONTENT)
