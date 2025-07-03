from django.shortcuts import render, get_object_or_404, redirect
from .models import CustomPage
import json
from django.views.decorators.csrf import csrf_exempt

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