# wages/models.py (or your app's models.py)

from django.db import models
from django.utils import timezone
from decimal import Decimal

class Tailor(models.Model):
    """Model for Tailor information."""
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)  # Phone can be optional

    class Meta:
        verbose_name = "Tailor"
        verbose_name_plural = "Tailors"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Model for Products/Services offered, now with differentiated pricing."""
    name = models.CharField(max_length=100)

    tailor_payment_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'), # Added default value for initial product creation
        help_text="Amount paid to tailor per piece"
    )

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['name']

    def __str__(self):
        return self.name



class DailyWork(models.Model):
    """Records daily work done by tailors, now with optional customer linkage."""
    # ForeignKeys use direct model names as they are defined above
    tailor = models.ForeignKey(Tailor, on_delete=models.CASCADE, related_name='daily_works')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='daily_works')
    customer_name = models.CharField(max_length=255, default='Unknown Customer')
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    ) # This 'rate' is what the tailor gets paid for THIS specific record (populated from product.tailor_payment_rate)
    date = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Daily Work Record"
        verbose_name_plural = "Daily Work Records"
        ordering = ['-date', 'tailor__name']

    @property
    def total(self):
        """Calculates the total amount for this daily work record."""
        return self.quantity * self.rate


class WorkRecord(models.Model):
    """Enhanced work record model with order integration and quality rating."""
    # ForeignKeys use direct model names as they are defined above
    tailor = models.ForeignKey(Tailor, on_delete=models.CASCADE, related_name='work_records')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='work_records') # Product this work was on
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2
    ) # This 'rate' is the actual rate paid for THIS specific work record (populated from product.tailor_payment_rate)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date = models.DateField(default=timezone.now)
    work_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Work Record"
        verbose_name_plural = "Work Records"
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.rate


        super().save(*args, **kwargs)

