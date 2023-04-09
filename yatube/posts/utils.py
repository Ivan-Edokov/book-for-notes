from django.conf import settings
from django.core.paginator import Paginator


def pagination(request, queryset):
    paginator = Paginator(queryset, settings.LIMIT_POST)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
