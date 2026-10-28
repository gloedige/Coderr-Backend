from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Offer(models.Model):
	"""A business user's service offer with up to three priced detail tiers."""

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='offers',
	)
	title = models.CharField(max_length=150)
	image = models.FileField(upload_to='uploads/', blank=True, null=True)
	description = models.CharField(max_length=500, blank=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		"""Return the offer title."""
		return self.title


class OfferDetail(models.Model):
	"""One basic, standard, or premium tier of an offer."""

	class OfferType(models.TextChoices):
		"""Allowed offer tiers."""

		BASIC = 'basic', 'Basic'
		STANDARD = 'standard', 'Standard'
		PREMIUM = 'premium', 'Premium'

	offer = models.ForeignKey(
		Offer,
		on_delete=models.CASCADE,
		related_name='details',
	)
	title = models.CharField(max_length=150)
	revisions = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(0), MaxValueValidator(100)]
	)
	delivery_time_in_days = models.PositiveSmallIntegerField(
		validators=[MinValueValidator(1), MaxValueValidator(365)]
	)
	price = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		validators=[
			MinValueValidator(Decimal('0.01')),
			MaxValueValidator(Decimal(100000)),
		],
	)
	features = models.JSONField(default=list, blank=True)
	offer_type = models.CharField(max_length=8, choices=OfferType.choices)

	class Meta:
		"""Enforce one detail per tier and valid price, delivery, and revision ranges."""

		constraints: ClassVar[list[models.BaseConstraint]] = [
			models.UniqueConstraint(
				fields=['offer', 'offer_type'], name='offer_detail_type_unique'
			),
			models.CheckConstraint(
				condition=models.Q(price__gt=0, price__lte=100000),
				name='offer_detail_price_range',
			),
			models.CheckConstraint(
				condition=models.Q(
					delivery_time_in_days__gte=1,
					delivery_time_in_days__lte=365,
				),
				name='offer_detail_delivery_range',
			),
			models.CheckConstraint(
				condition=models.Q(revisions__gte=0, revisions__lte=100),
				name='offer_detail_revisions_max',
			),
		]

	def __str__(self):
		"""Return the offer title with the tier name."""
		return f'{self.offer.title} - {self.get_offer_type_display()}'


class Order(models.Model):
	"""A customer's purchase with a snapshot of the purchased offer detail."""

	class Status(models.TextChoices):
		"""Allowed order states."""

		IN_PROGRESS = 'in_progress', 'In progress'
		COMPLETED = 'completed', 'Completed'
		CANCELLED = 'cancelled', 'Cancelled'

	customer_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='customer_orders',
	)
	business_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='business_orders',
	)
	title = models.CharField(max_length=150)
	revisions = models.PositiveSmallIntegerField()
	delivery_time_in_days = models.PositiveSmallIntegerField()
	price = models.DecimalField(max_digits=8, decimal_places=2)
	features = models.JSONField(default=list, blank=True)
	offer_type = models.CharField(max_length=8, choices=OfferDetail.OfferType.choices)
	status = models.CharField(
		max_length=16,
		choices=Status.choices,
		default=Status.IN_PROGRESS,
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		"""Order newest orders first."""

		ordering = ('-created_at', '-pk')

	def __str__(self):
		"""Return the order title with its status label."""
		return f'{self.title} ({self.get_status_display()})'


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
