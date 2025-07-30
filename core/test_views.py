from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, HttpResponseServerError
from core.error_handlers import handler404, handler500, handler403, handler400, handler401

@csrf_exempt
def test_404(request):
    """Тестовая view для 404 ошибки"""
    return handler404(request)

@csrf_exempt
def test_500(request):
    """Тестовая view для 500 ошибки"""
    return handler500(request)

@csrf_exempt
def test_403(request):
    """Тестовая view для 403 ошибки"""
    return handler403(request)

@csrf_exempt
def test_400(request):
    """Тестовая view для 400 ошибки"""
    return handler400(request)

@csrf_exempt
def test_401(request):
    """Тестовая view для 401 ошибки"""
    return handler401(request)

@csrf_exempt
def test_502(request):
    """Тестовая view для 502 ошибки"""
    return render(request, '502.html', status=502)

@csrf_exempt
def test_503(request):
    """Тестовая view для 503 ошибки"""
    return render(request, '503.html', status=503)

def test_index(request):
    """Главная страница для тестирования ошибок"""
    test_pages = [
        {'url': '/test/404/', 'name': '404 - Страница не найдена', 'color': 'blue'},
        {'url': '/test/400/', 'name': '400 - Неверный запрос', 'color': 'purple'},
        {'url': '/test/401/', 'name': '401 - Требуется авторизация', 'color': 'yellow'},
        {'url': '/test/403/', 'name': '403 - Доступ запрещен', 'color': 'orange'},
        {'url': '/test/500/', 'name': '500 - Ошибка сервера', 'color': 'red'},
        {'url': '/test/502/', 'name': '502 - Ошибка шлюза', 'color': 'indigo'},
        {'url': '/test/503/', 'name': '503 - Сервис недоступен', 'color': 'gray'},
    ]
    
    return render(request, 'test_index.html', {'test_pages': test_pages})

# Preview views (без HTTP статуса ошибки)
def preview_404(request):
    """Предварительный просмотр 404 страницы"""
    return render(request, '404.html')

def preview_400(request):
    """Предварительный просмотр 400 страницы"""
    return render(request, '400.html')

def preview_401(request):
    """Предварительный просмотр 401 страницы"""
    return render(request, '401.html')

def preview_403(request):
    """Предварительный просмотр 403 страницы"""
    return render(request, '403.html')

def preview_500(request):
    """Предварительный просмотр 500 страницы"""
    return render(request, '500.html')

def preview_502(request):
    """Предварительный просмотр 502 страницы"""
    return render(request, '502.html')

def preview_503(request):
    """Предварительный просмотр 503 страницы"""
    return render(request, '503.html')

def debug_templates(request):
    """Отладочная view для проверки шаблонов"""
    try:
        # Пробуем рендерить 404 шаблон
        response = render(request, '404.html')
        return HttpResponse(f"✅ Шаблон 404.html найден и рендерится успешно!<br>Размер: {len(response.content)} байт")
    except Exception as e:
        return HttpResponse(f"❌ Ошибка при рендеринге 404.html: {str(e)}") 