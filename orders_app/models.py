# Third-party
from django.conf import settings
from django.db import models

# Local imports
from offers_app.models import OfferDetail

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