from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest

def handler404(request, exception=None):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def handler500(request, exception=None):
    """Custom 500 error handler"""
    return render(request, '500.html', status=500)

def handler403(request, exception=None):
    """Custom 403 error handler"""
    return render(request, '403.html', status=403)

def handler400(request, exception=None):
    """Custom 400 error handler"""
    return render(request, '400.html', status=400)

def handler502(request, exception=None):
    """Custom 502 error handler"""
    return render(request, '502.html', status=502)

def handler503(request, exception=None):
    """Custom 503 error handler"""
    return render(request, '503.html', status=503)

def handler401(request, exception=None):
    """Custom 401 error handler"""
    return render(request, '401.html', status=401) 