from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField


class RegistrationPage(Page):
    header_text = RichTextField(blank=True)

    content_panels = Page.content_panels + ["header_text"]

    def serve(self, request):
        from django.shortcuts import render
        return render(request, 'register.html', {
            'page': self,
            'errors': {},
            'data': {}
        })
