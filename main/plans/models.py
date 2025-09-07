# plans/models.py
from django.db import models
from user.models import User
from datetime import timedelta, date


class PremiumPlan(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # ₹999.00
    duration = models.PositiveIntegerField(help_text="Duration in days")  # e.g. 30, 90, 365
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price"]
        verbose_name = "Premium Plan"
        verbose_name_plural = "Premium Plans"

    def __str__(self):
        return f"{self.name} (₹{self.price} / {self.duration} days)"


class PlanFeature(models.Model):
    plan = models.ForeignKey(PremiumPlan, related_name="features", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Plan Feature"
        verbose_name_plural = "Plan Features"

    def __str__(self):
        return f"{self.plan.name} → {self.name}"


class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(PremiumPlan, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "User Subscription"
        verbose_name_plural = "User Subscriptions"

    def __str__(self):
        if self.plan:
            return f"{self.user.username} → {self.plan.name}"
        return f"{self.user.username} → No Plan"

    def activate(self, plan: PremiumPlan):
        """Activate or renew a subscription for a given plan."""
        self.plan = plan
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=plan.duration)
        self.is_active = True
        self.save()

    def deactivate(self):
        """Deactivate the subscription (manually or expired)."""
        self.is_active = False
        self.save()

    def has_active_subscription(self):
        """Check if subscription is still valid (date + status)."""
        if self.is_active and self.end_date and self.end_date >= date.today():
            return True
        return False
