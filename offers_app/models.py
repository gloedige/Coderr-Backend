# Standard library
from decimal import Decimal
from typing import ClassVar

# Third-party
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

	class Meta:
		"""Order offers by most recent update with the primary key as tiebreaker."""

		ordering = ('-updated_at', 'pk')

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