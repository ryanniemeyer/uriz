# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^(?P<token>[\w]+)\+/?$', 'uriz.views.url_info',
        name='url_info'),
    url(r'^(?P<token>[\w]+)/?$', 'uriz.views.url_redirect',
        name='url_redirect'),
    url(r'^$', 'uriz.views.index',
        name='uriz'),
)
