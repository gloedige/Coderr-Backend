# Third-party
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Local imports
from core.utils import handle_internal_errors
from reviews_app.api.permissions import IsCustomerUser, IsReviewCreatorOrReadOnly
from reviews_app.api.serializers import (
    ReviewCreateSerializer,
    ReviewReadSerializer,
    ReviewUpdateSerializer,
)
from reviews_app.models import Review


REVIEW_QUERY_PARAMETERS = {
    'business_user_id', 'reviewer_id', 'ordering',
}
REVIEW_ORDERING = {
    'updated_at': 'updated_at',
    '-updated_at': '-updated_at',
    'rating': 'rating',
    '-rating': '-rating',
}


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Expose authenticated review list/create/update/delete API operations."""

    queryset = Review.objects.select_related('business_user', 'reviewer')
    serializer_class = ReviewReadSerializer
    lookup_value_regex = r'\d+'
    permission_classes = (IsAuthenticated, IsReviewCreatorOrReadOnly)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head', 'options')

    def get_permissions(self):
        """Require the customer role for create; otherwise use the default permissions."""
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomerUser()]
        return super().get_permissions()

    def get_serializer_class(self):
        """Return the write serializer for create and the read serializer otherwise."""
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewReadSerializer

    def get_queryset(self):
        """Return all reviews; for the list action apply validated filters and ordering."""
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset
        return self.filtered_reviews(queryset)

    def filtered_reviews(self, queryset):
        """Validate query parameters, then filter and order `queryset`."""
        self.validate_query_parameters()
        return self.apply_ordering(self.apply_filters(queryset))

    def validate_query_parameters(self):
        """Validate allowed query keys and ordering values, raising a field error."""
        params = self.request.query_params
        unknown = set(params) - REVIEW_QUERY_PARAMETERS
        if unknown:
            raise ValidationError(
                {'query': f'Unknown query parameter(s): {", ".join(sorted(unknown))}.'}
            )
        if params.get('ordering', '-updated_at') not in REVIEW_ORDERING:
            raise ValidationError({'ordering': 'Unsupported ordering value.'})

    def apply_filters(self, queryset):
        """Apply optional business-user and reviewer integer filters."""
        for parameter in ('business_user_id', 'reviewer_id'):
            value = self.request.query_params.get(parameter)
            if value is not None:
                queryset = queryset.filter(**{parameter: self.parse_id(parameter, value)})
        return queryset

    def apply_ordering(self, queryset):
        """Order reviews by an allowed field and primary key for stable results."""
        ordering = self.request.query_params.get('ordering', '-updated_at')
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

    @handle_internal_errors('Review list failed due to an internal error.')
    def list(self, request, *args, **kwargs):
        """Return filtered, ordered review data for the authenticated requester."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a review after validating the request data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.save_review(serializer)

    @handle_internal_errors('Review creation failed due to an internal error.')
    def save_review(self, serializer):
        """Persist the review and return 201 with its data."""
        data = ReviewReadSerializer(serializer.save()).data
        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Partially update a review when requested by its creator."""
        review = self.get_object()
        serializer = ReviewUpdateSerializer(
            data=request.data, context={'review': review}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return self.save_review_update(serializer)

    @handle_internal_errors('Review update failed due to an internal error.')
    def save_review_update(self, serializer):
        """Persist validated changes and return the updated review."""
        return Response(ReviewReadSerializer(serializer.update_review()).data)

    def destroy(self, request, *args, **kwargs):
        """Delete the review if owned by the requester, returning 204."""
        return self.delete_review(self.get_object())

    @handle_internal_errors('Review deletion failed due to an internal error.')
    def delete_review(self, review):
        """Delete `review` and return an empty 204 response."""
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
