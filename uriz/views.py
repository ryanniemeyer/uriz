# -*- coding: utf-8 -*-

from boto.dynamodb import exceptions as dynamodb_exceptions
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _lazy

import boto
import datetime
import random
import time

class ShortenURLForm(forms.Form):
    url = forms.URLField(min_length=11, max_length=8192, label='',
                         widget=forms.TextInput(attrs={'size':'60',
                                                       'autofocus':'autofocus',
                                                       'placeholder':_lazy("URL")}))

def index(request):
    """View for displaying uriz.in homepage and POSTing new URLs."""
    if request.method == "GET":
        form = ShortenURLForm()
    else:
        form = ShortenURLForm(request.POST)
        if form.is_valid():
            short_url_token = _ensure_url(form.cleaned_data['url'])
            return redirect(reverse('url_info',
                                    args=[short_url_token]))

    return render(request, 'uriz/index.html', {'form':form})

def url_redirect(request, token):
    """View for redirecting from short URL to long."""
    url_info = _fetch_url_info(token)
    
    # Increment visit counter
    url_info.add_attribute('visits', 1)
    url_info.save()

    return redirect(url_info['long_url'])

def url_info(request, token):
    """View for showing stats about a shortened URL."""
    url_info = _fetch_url_info(token)
    url_info['created'] = datetime.datetime.utcfromtimestamp(url_info['created'])
    return render(request, 'uriz/url_info.html',
                  {'url_info':url_info})

def _fetch_url_info(token):
    """Fetches the URL info for the given token, raising Http404 if not found."""
    uriz_table = _get_dynamo_connection().get_table('uriz')

    try:
        return uriz_table.get_item(hash_key=token)
    except dynamodb_exceptions.DynamoDBKeyNotFoundError:
        raise Http404

def _fetch_token(long_url, conn):
    """Fetches the short token for the given URL, returning None if not found."""
    uriz_long_table = conn.get_table('uriz_long')

    try:
        return uriz_long_table.get_item(hash_key=long_url)['token']
    except dynamodb_exceptions.DynamoDBKeyNotFoundError:
        return None

def _ensure_url(long_url):
    """Ensures there's a short token for the given URL and returns it.
    
    If one doesn't already exist, creates a new one.

    """
    conn = _get_dynamo_connection()
    token = _fetch_token(long_url, conn)
    return token if token else _add_url(long_url, conn)

def _add_url(long_url, conn):
    token_len = getattr(settings, 'DEFAULT_SHORT_TOKEN_LENGTH', 5)
    default_len_tries = 0
    table = conn.get_table('uriz')

    # Keep trying to add a short token until successful. After a few
    # tries, start using longer and longer tokens until we find a
    # unique one.
    while True:
        token = _random_token(token_len)
        if not table.has_item(token):
            short_url_info = {
                'token': token,
                'created':int(round(time.time())),
                'long_url': long_url,
                'visits': 0,
            }
            short_url = table.new_item(attrs=short_url_info)
            short_url.put()
            break
        else:
            if default_len_tries > 4:
                token_len += 1
            else:
                default_len_tries += 1

    # Add a reverse index for this short token
    long_url_table = conn.get_table('uriz_long')
    long_url_info = {
        'long_url':long_url,
        'token':token,
    }
    long_url = long_url_table.new_item(attrs=long_url_info)
    long_url.put()

    return token

def _get_dynamo_connection():
    return boto.connect_dynamodb(aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

_ID_NUMS = ('2','3','4','5','6','7','8','9')
_ID_CHARS = ('a','b','c','d','e','f','g','h','i','j','k','m','n','p','q','r',
             's','t','u','v','w','x','y','z','A','B','C','D','E','F','G','H',
             'I','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y',
             'Z')

_ID_ALPHANUM = _ID_NUMS + _ID_CHARS

def _random_token(token_len):
    """
    Returns a random String of alphanumeric characters such that every 3rd
    character is a random integer (to reduce chances of the random id having
    a bad word in it). This method also doesn't use a few characters
    (e.g. 0,O) because they're hard for people to distinguish sometimes.

    """

    token = random.choice(_ID_ALPHANUM)
    next_char = 2
    while next_char <= token_len:
        if next_char % 3 == 0:
            # Make sure every 3rd character is a number to reduce chances
            # of the token having an actual English word
            token += random.choice(_ID_NUMS)
        else:
            token += random.choice(_ID_ALPHANUM)

        next_char += 1

    return token
