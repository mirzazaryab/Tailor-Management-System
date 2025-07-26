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
    customer_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'), # Added default value for initial product creation
        help_text="Price charged to customer per piece"
    )
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


class Customer(models.Model):
    """Customer model for order management."""
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)  # Phone should be unique for customer identification
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)  # Allow null and blank for address
    city = models.CharField(max_length=100, default='', blank=True)  # Allow blank for city
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['name']

    def __str__(self):
        return self.name

    def total_orders_count(self):
        """Returns the total number of orders placed by this customer."""
        # Correctly uses the related_name 'orders' defined in the Order model
        return self.orders.count()

    def total_spent_amount(self):
        """Returns the total amount spent by this customer across all orders."""
        # Correctly uses the related_name 'orders' defined in the Order model
        return self.orders.aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0.00')


class Order(models.Model):
    """Main order model."""
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('ready_for_delivery', 'Ready for Delivery'),
        ('completed', 'Completed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Customer model is defined above, so no string literal needed for ForeignKey
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    order_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    advance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-order_date', '-created_at']

    def save(self, *args, **kwargs):
        # Generate order number if it's a new order (only once)
        if not self.order_number:
            year = timezone.now().year
            last_order = Order.objects.filter(
                order_number__startswith=f'ORD-{year}-'
            ).order_by('order_number').last()

            if last_order:
                try:
                    last_num = int(last_order.order_number.split('-')[-1])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1 # Fallback if parsing fails (e.g., first order or malformed)
            else:
                new_num = 1 # First order of the year
            self.order_number = f'ORD-{year}-{new_num:04d}'

        is_new_instance = self.pk is None # Check if this is a new object being saved for the first time
        super().save(*args, **kwargs) # Save the order first to ensure it has a primary key

        if not is_new_instance and self.items.exists(): # Only update if order is existing and has items
            current_total_from_items = self.items.aggregate(total=models.Sum(models.F('quantity') * models.F('rate')))[
                                'total'] or Decimal('0.00')
            if self.total_amount != current_total_from_items:
                self.total_amount = current_total_from_items
                # Use update_fields to prevent infinite recursion if save() is called again
                super().save(update_fields=['total_amount'])

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer.name}"

    def remaining_amount(self):
        """Calculates the outstanding amount for the order."""
        return self.total_amount - self.advance_payment

    def is_overdue(self):
        """Checks if the order is overdue based on delivery date and status."""
        return (self.delivery_date < timezone.now().date() and
                self.status not in ['completed', 'delivered', 'cancelled'])

    def completion_percentage(self):
        """Calculates the percentage of completed order items."""
        total_items = self.items.count()
        if total_items == 0:
            return 0
        completed_items = self.items.filter(status='completed').count()
        return int((completed_items / total_items) * 100)

    def get_status_display_class(self):
        """Returns a Bootstrap class for status display (e.g., 'warning', 'success')."""
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'in_progress': 'primary',
            'ready_for_delivery': 'success',
            'completed': 'success',
            'delivered': 'secondary',
            'cancelled': 'danger',
        }
        return status_classes.get(self.status, 'secondary')

    def get_priority_display_class(self):
        """Returns a Bootstrap class for priority display."""
        priority_classes = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'urgent': 'danger',
        }
        # Fixed indentation for the return statement
        return priority_classes.get(self.priority, 'secondary')


class DailyWork(models.Model):
    """Records daily work done by tailors, now with optional customer linkage."""
    # ForeignKeys use direct model names as they are defined above
    tailor = models.ForeignKey(Tailor, on_delete=models.CASCADE, related_name='daily_works')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='daily_works')
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    ) # This 'rate' is what the tailor gets paid for THIS specific record (populated from product.tailor_payment_rate)
    date = models.DateField(default=timezone.now)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_work_records'
    )

    class Meta:
        verbose_name = "Daily Work Record"
        verbose_name_plural = "Daily Work Records"
        ordering = ['-date', 'tailor__name']

    @property
    def total(self):
        """Calculates the total amount for this daily work record."""
        return self.quantity * self.rate

    def __str__(self):
        customer_info = f" for {self.customer.name}" if self.customer else ""
        return f"{self.tailor.name} - {self.quantity} {self.product.name} on {self.date}{customer_info}"


class OrderItem(models.Model):
    """Individual items within an order."""
    # ForeignKeys use direct model names as they are defined above
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2
    ) # This 'rate' is what the customer pays for THIS specific item (populated from product.customer_price or adjusted)
    total = models.DecimalField(max_digits=10, decimal_places=2, editable=False) # Stores quantity * rate

    assigned_tailor = models.ForeignKey(
        Tailor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_order_items'
    )

    ITEM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned to Tailor'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('quality_check', 'Quality Check'),
        ('approved', 'Approved'),
        ('rework', 'Needs Rework'),
    ]
    status = models.CharField(max_length=20, choices=ITEM_STATUS_CHOICES, default='pending')
    measurements = models.JSONField(default=dict, blank=True, null=True)
    special_instructions = models.TextField(blank=True, null=True)
    assigned_date = models.DateTimeField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.rate
        super().save(*args, **kwargs)

        # WARNING: Direct calls to save() on related objects within another save() can cause
        # infinite recursion or inefficient queries. For robust production systems,
        # consider using Django Signals (post_save/post_delete on OrderItem) to trigger
        # Order.total_amount recalculation.
        if self.order:
            self.order.save() # This triggers the Order's save method to recalculate its total_amount

    def __str__(self):
        return f"{self.order.order_number} - {self.product.name} (Qty: {self.quantity})"

    def get_status_display_class(self):
        """Returns a Bootstrap class for item status display."""
        status_classes = {
            'pending': 'secondary',
            'assigned': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'quality_check': 'primary',
            'approved': 'success',
            'rework': 'danger',
        }
        return status_classes.get(self.status, 'secondary')


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

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_records_for_item'
    )
    is_order_work = models.BooleanField(default=False) # Indicates if this work is linked to an order item
    work_type = models.CharField(max_length=20, choices=[
        ('order', 'Order Work'),
        ('custom', 'Custom Work'),
    ], default='custom')

    # This field was previously missing and is now correctly included
    quality_rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], # Choices for 1 to 5 stars
        default=5,
        help_text="Quality rating for the work (1-5)"
    )

    work_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Work Record"
        verbose_name_plural = "Work Records"
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.rate

        if self.order_item:
            self.is_order_work = True
            self.work_type = 'order'
        else:
            self.is_order_work = False
            self.work_type = 'custom'

        super().save(*args, **kwargs)

        # WARNING: Direct calls to save() on related objects within another save() can cause
        # infinite recursion or inefficient queries. For robust production systems,
        # consider using a Django Signal (post_save on WorkRecord) to trigger
        # OrderItem status updates.
        if self.order_item:
            total_quantity_recorded = WorkRecord.objects.filter(
                order_item=self.order_item
            ).aggregate(total=models.Sum('quantity'))['total'] or 0

            # Only update OrderItem status if sufficient quantity is recorded and status is not already final
            if total_quantity_recorded >= self.order_item.quantity:
                if self.order_item.status not in ['completed', 'quality_check', 'approved', 'rework']:
                    self.order_item.status = 'completed'
                    self.order_item.completed_date = timezone.now()
                    self.order_item.save()
            # If item was assigned and work is starting, set to in_progress
            elif self.order_item.status == 'assigned':
                self.order_item.status = 'in_progress'
                if not self.order_item.started_date: # Only set started_date once
                    self.order_item.started_date = timezone.now()
                self.order_item.save()

    def __str__(self):
        if self.order_item:
            return f"Work by {self.tailor.name} on {self.order_item.product.name} (Order #{self.order_item.order.order_number})"
        return f"Custom Work by {self.tailor.name} - {self.product.name}"


class OrderPayment(models.Model):
    """Track payments for orders."""
    PAYMENT_TYPE_CHOICES = [
        ('advance', 'Advance Payment'),
        ('partial', 'Partial Payment'),
        ('final', 'Final Payment'),
        ('refund', 'Refund'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('jazzCash', 'Jazz Cash'),
        ('easyPaisa', 'Easy Paisa'),
        ('other', 'Other'),
    ]

    # Order model is defined above, so no string literal needed
    order = models.ForeignKey(Order, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order Payment"
        verbose_name_plural = "Order Payments"
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment of Rs. {self.amount} ({self.payment_type}) for Order #{self.order.order_number}"
