from django import forms
from plans.models import PremiumPlan, PlanFeature

class PremiumPlanCreationForm(forms.ModelForm):
    features = forms.ModelMultipleChoiceField(
        queryset=PlanFeature.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select features included in this plan"
    )

    class Meta:
        model = PremiumPlan
        fields = ["name", "price", "duration", "description", "is_active", "features"]
