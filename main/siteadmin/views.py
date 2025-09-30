from .models import CustomPage
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from plans.models import PremiumPlan
from siteadmin.forms import PremiumPlanCreationForm


@staff_member_required
def create_premium_plan(request):
    if request.method == "POST":
        form = PremiumPlanCreationForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.save()
            form.save_m2m()  # Save the many-to-many relationship (features)

            messages.success(request, f"Premium Plan '{plan.name}' was created successfully!")
            return redirect("siteadmin_create_plan")  # Or to some admin dashboard
    else:
        form = PremiumPlanCreationForm()

    return render(request, "siteadmin/create_premium_plan.html", {"form": form})


def page_list(request):
    pages = CustomPage.objects.all()
    return render(request, 'siteadmin/page_list.html', {'pages': pages})

def page_edit(request, pk):
    page = get_object_or_404(CustomPage, pk=pk)    
    if request.method == 'POST':
        layout = request.POST.get("layout_json")
        if layout:
            page.layout = json.loads(layout)
            page.save()
            return redirect('custom_page_list')
    return render(request, 'siteadmin/page_edit.html', {'page': page})

def page_render(request, slug):
    page = get_object_or_404(CustomPage, slug=slug)
    return render(request, 'siteadmin/page_render.html', {'page': page, 'layout': page.layout})

@csrf_exempt
def page_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', 'Untitled Page')
        slug = request.POST.get('slug', '')
        layout_json = request.POST.get('layout_json', '[]')
        page = CustomPage.objects.create(
            title=title,
            slug=slug,
            layout=json.loads(layout_json)
        )
        return redirect('custom_page_edit', pk=page.pk)

    return render(request, 'siteadmin/page_create.html')