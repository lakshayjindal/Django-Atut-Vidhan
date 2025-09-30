# plans/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PremiumPlan, Payment, UserSubscription
from datetime import date


@login_required
def plans_list(request):
    """Show all available premium plans"""
    plans = PremiumPlan.objects.filter(is_active=True)
    user_subscription = getattr(request.user, "subscription", None)
    return render(request, "plans/premiumplans.html", {
        "plans": plans,
        "user_subscription": user_subscription,
    })


@login_required
def make_payment(request, plan_id):
    """Payment page for a specific plan"""
    plan = get_object_or_404(PremiumPlan, id=plan_id, is_active=True)

    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        screenshot_url = request.POST.get("screenshot")  # you’re storing URL instead of file

        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            transaction_id=transaction_id,
            screenshot=screenshot_url,
            status="pending",  # default
        )

        messages.info(request, "Your payment has been submitted and is pending verification.")
        return redirect("plans_list")

    return render(request, "plans/make_payment.html", {"plan": plan})


@login_required
def my_subscription(request):
    """Show user’s current subscription and payment history"""
    subscription = getattr(request.user, "subscription", None)
    payments = request.user.payments.all()
    return render(request, "plans/my_subscription.html", {
        "subscription": subscription,
        "payments": payments,
    })


# --------------------
# ADMIN / STAFF VIEWS
# --------------------

@login_required
def verify_payment(request, payment_id, action):
    """
    Admin view to verify payments.
    action = "approve" -> mark success + activate subscription
    action = "reject"  -> mark failed
    """
    if not request.user.is_staff:
        messages.error(request, "Unauthorized.")
        return redirect("plans_list")

    payment = get_object_or_404(Payment, id=payment_id)

    if action == "approve":
        payment.status = "success"
        payment.save()

        # Activate or renew subscription
        subscription, created = UserSubscription.objects.get_or_create(user=payment.user)
        subscription.activate(payment.plan)

        messages.success(request, f"Payment approved and subscription activated for {payment.user.username}.")
    elif action == "reject":
        payment.status = "failed"
        payment.save()
        messages.warning(request, f"Payment rejected for {payment.user.username}.")

    return redirect("admin_payments_list")  # you can create a page for all pending payments
