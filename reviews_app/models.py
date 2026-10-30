# Standard library
from decimal import Decimal
from typing import ClassVar

# Third-party
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Review(models.Model):
	"""A customer's rating and comment for a business user."""

	business_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='received_reviews',
	)
	reviewer = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='written_reviews',
	)
	rating = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(1), MaxValueValidator(5)]
	)
	description = models.CharField(max_length=500)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		"""Limit ratings to 1-5 and allow one review per reviewer and business."""

		constraints: ClassVar[list[models.BaseConstraint]] = [
			models.CheckConstraint(
				condition=models.Q(rating__gte=1, rating__lte=5),
				name='review_rating_range',
			),
			models.UniqueConstraint(
				fields=['business_user', 'reviewer'],
				name='review_active_business_reviewer_unique',
			)
		]

	def __str__(self):
		"""Return a compact label naming the rating, reviewer, and business user."""
		return f'{self.rating}/5 review by {self.reviewer_id} for {self.business_user_id}'