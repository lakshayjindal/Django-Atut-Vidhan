# plans/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import PremiumPlan, UserSubscription
from django.contrib import messages


def premium_plans(request):
    """Show all active premium plans."""
    plans = PremiumPlan.objects.filter(is_active=True).prefetch_related("features")
    context = {
        "plans": plans,
    }
    return render(request, "plans/premiumplans.html", context)



def subscribe_plan(request, plan_id):
    """(Stub) Subscribe the logged-in user to a plan.
    Later this will integrate with payment gateway.
    """
    if request.user.is_authenticated:

        plan = get_object_or_404(PremiumPlan, id=plan_id, is_active=True)

        subscription, created = UserSubscription.objects.get_or_create(user=request.user)

        # ⚠️ Payment handling will go here later
        # For now, directly activate (development mode)
        subscription.activate(plan)

        return redirect("premium_plans")
    else:
        messages.error(request, "You are not logged in.")
        return redirect("login")