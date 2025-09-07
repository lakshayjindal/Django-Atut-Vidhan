from django.contrib import admin
from . import models
# Register your models here.
admin.site.register(models.PremiumPlan)
admin.site.register(models.UserSubscription)
admin.site.register(models.PlanFeature)