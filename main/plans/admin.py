from django.contrib import admin
from . import models


@admin.register(models.PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "get_plans"]

    def get_plans(self, obj):
        return ", ".join([plan.name for plan in obj.plans.all()])

    get_plans.short_description = "Included in Plans"


@admin.register(models.PremiumPlan)
class PremiumPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "duration", "is_active", "get_features"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]

    def get_features(self, obj):
        return ", ".join([feature.name for feature in obj.features.all()])

    get_features.short_description = "Features"


@admin.register(models.UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "start_date", "end_date", "is_active"]
    list_filter = ["is_active", "start_date", "end_date"]
    search_fields = ["user__username", "plan__name"]
