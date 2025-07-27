from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def querystring_without_page(context):
    querydict = context['request'].GET.copy()
    querydict.pop('page', None)
    return urlencode(querydict)