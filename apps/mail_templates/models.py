# mailer_templates/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone
from bs4 import BeautifulSoup
import re
import os
import uuid

class EmailTemplate(models.Model):
    """
    Шаблон письма:
      - id                  — автоматически PK
      - owner               — владелец шаблона (пользователь)
      - title               — название шаблона
      - html_content        — HTML-контент (для рендеринга)
      - ck_content          — оригинальный контент CKEditor (если нужно хранить отдельно)
      - plain_text_content  — текстовая версия письма
      - is_draft            — флаг черновика
      - send_count          — сколько раз отправлялся
      - created_at, updated_at — метки времени
    """
    owner               = models.ForeignKey(
                              settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='email_templates'
                          )
    title               = models.CharField(
                              max_length=200,
                              help_text="Название шаблона"
                          )
    html_content        = models.TextField(
                              help_text="HTML-контент, используется для рендеринга письма"
                          )
    ck_content          = models.TextField(
                              blank=True,
                              help_text="Исходный контент из CKEditor (если нужен отдельно)"
                          )
    plain_text_content  = models.TextField(
                              blank=True,
                              help_text="Текстовая версия письма без HTML"
                          )
    is_draft            = models.BooleanField(
                              default=True,
                              help_text="Шаблон сохраняется как черновик"
                          )
    send_count          = models.PositiveIntegerField(
                              default=0,
                              help_text="Сколько раз использован для рассылки"
                          )
    created_at          = models.DateTimeField(
                              auto_now_add=True,
                              help_text="Когда шаблон создан"
                          )
    updated_at          = models.DateTimeField(
                              auto_now=True,
                              help_text="Когда последний раз сохранялся"
                          )

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('owner', 'title')
        verbose_name = "Email шаблон"
        verbose_name_plural = "Email шаблоны"

    def __str__(self):
        return f"{self.title} ({self.owner})"

    def get_html_with_tracking(self, tracking_id):
        """Добавляет трекинг-пиксель в HTML письма"""
        tracking_pixel = f'<img src="http://localhost:8000/track/open/{tracking_id}" width="1" height="1" style="display:none" />'
        
        # Добавляем пиксель перед закрывающим тегом body
        if '</body>' in self.html_content:
            return self.html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            return self.html_content + tracking_pixel

    def get_html_with_click_tracking(self, tracking_id):
        """Заменяет все ссылки на отслеживаемые"""
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Находим все ссылки
        for link in soup.find_all('a', href=True):
            original_url = link['href']
            # Создаем отслеживаемую ссылку
            tracked_url = f'http://localhost:8000/track/click/{tracking_id}?url={original_url}'
            link['href'] = tracked_url

        return str(soup)


def template_image_upload_path(instance, filename):
    """Генерирует путь для загрузки изображений шаблонов"""
    # Получаем расширение файла
    ext = filename.split('.')[-1]
    # Создаем уникальное имя файла
    unique_filename = f"{uuid.uuid4()}.{ext}"
    # Возвращаем путь: media/template_images/user_id/unique_filename
    return os.path.join('template_images', str(instance.owner.id), unique_filename)


class TemplateImage(models.Model):
    """
    Изображения для шаблонов писем:
      - id          — автоматически PK
      - owner       — владелец изображения (пользователь)
      - image       — файл изображения
      - filename    — оригинальное имя файла
      - file_size   — размер файла в байтах
      - width       — ширина изображения
      - height      — высота изображения
      - alt_text    — альтернативный текст
      - created_at  — когда загружено
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='template_images'
    )
    image = models.ImageField(
        upload_to=template_image_upload_path,
        help_text="Загруженное изображение"
    )
    filename = models.CharField(
        max_length=255,
        help_text="Оригинальное имя файла"
    )
    file_size = models.PositiveIntegerField(
        help_text="Размер файла в байтах"
    )
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Ширина изображения в пикселях"
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Высота изображения в пикселях"
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Альтернативный текст для изображения"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Когда изображение загружено"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Изображение шаблона"
        verbose_name_plural = "Изображения шаблонов"

    def __str__(self):
        return f"{self.filename} ({self.owner})"

    def get_url(self):
        """Возвращает URL изображения"""
        return self.image.url

    def get_file_size_mb(self):
        """Возвращает размер файла в МБ"""
        return round(self.file_size / (1024 * 1024), 2)

    def get_dimensions(self):
        """Возвращает размеры изображения в виде строки"""
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "Неизвестно"
