import logging
import re
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import get_template

from django.http import HttpResponse
from django.contrib.auth import get_user_model, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import cache_page
from elasticsearch_dsl import Search, Q

from imageledger import forms, search, licenses, models

log = logging.getLogger(__name__)

CACHE_STATS_DURATION = 60 * 60  # 1 hour
CACHE_STATS_NAME = 'provider-stats'

def about(request):
    """Information about the current site, its goals, and what content is loaded"""
    # Provider counts
    providers = cache.get_or_set(CACHE_STATS_NAME, [], CACHE_STATS_DURATION)
    if not providers:
        for provider in sorted(settings.PROVIDERS.keys()):
            s = Search()
            q = Q('term', provider=provider)
            s = s.query(q)
            response = s.execute()
            if response.hits.total > 0:
                data = settings.PROVIDERS[provider]
                total = intcomma(response.hits.total)
                data.update({'hits': total})
                providers.append(data)
        # All results
        s = Search()
        response = s.execute()
        total = intcomma(response.hits.total)
        providers.append({'display_name': 'Total', 'hits': total})
        cache.set(CACHE_STATS_NAME, providers)
    return render(request, "about.html", {'providers': providers})

@login_required
def profile(request):
    counts = {}
    counts['lists'] = models.List.objects.filter(owner=request.user).count()
    counts['favorites'] = models.Favorite.objects.filter(user=request.user).count()
    counts['tags'] = models.UserTags.objects.filter(user=request.user).count()
    return render(request, "profile.html", {'user': request.user,
                                            'counts': counts})


@login_required
@require_POST
def delete_account(request):
    user = get_user_model().objects.get(username=request.user.username)
    logout(request)
    user.delete()
    return redirect(reverse('index'))

def health(request):
    return HttpResponse('OK')

@cache_page(60 * 60)  # 1 hour
def robots(request):
    out = get_template("robots.txt").render()
    return HttpResponse(out, content_type="text/plain")

def intcomma(value):
    # Adapted from https://github.com/django/django/blob/master/django/contrib/humanize/templatetags/humanize.py
    orig = str(value)
    new = re.sub(r"^(-?\d+)(\d{3})", r'\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)
