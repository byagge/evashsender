# mailer/views.py

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
import json
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from .models import ContactList, Contact
from .serializers import ContactListSerializer, ContactSerializer
from .utils import parse_emails, classify_email
from apps.billing.models import Plan


class ContactListViewSet(viewsets.ModelViewSet):
    """
    CRUD для ContactList и вложенные операции с Contact через @action.
    """
    serializer_class    = ContactListSerializer
    permission_classes  = [IsAuthenticated]
    parser_classes      = [MultiPartParser] + viewsets.ModelViewSet.parser_classes

    def get_queryset(self):
        return ContactList.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Переопределяем метод создания, чтобы при дублировании имени вернуть 400 с ошибкой,
        вместо падения 500.
        """
        # Подготовим сериализатор (owner запишем в perform_create)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {'name': ['Список с таким именем уже существует']},
                status=status.HTTP_400_BAD_REQUEST
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


    @action(detail=True, methods=['get', 'post'], url_path='contacts')
    def contacts(self, request, pk=None):
        """
        GET  /contactlists/{pk}/contacts/  — список контактов
        POST /contactlists/{pk}/contacts/  — добавить контакт { email, status }
        """
        contact_list = self.get_object()

        if request.method == 'GET':
            qs = contact_list.contacts.all()
            ser = ContactSerializer(qs, many=True)
            return Response(ser.data)

        # --- ОГРАНИЧЕНИЕ ПО ТАРИФУ ---
        user = request.user
        plan = getattr(user, 'current_plan', None)
        if not plan:
            return Response({'error': 'Не найден тариф пользователя.'}, status=status.HTTP_400_BAD_REQUEST)
        contact_limit = getattr(plan, 'subscribers', 0)
        # Считаем общее число контактов во всех списках пользователя
        total_contacts = Contact.objects.filter(contact_list__owner=user).count()
        if contact_limit and total_contacts >= contact_limit:
            return Response({'error': f'Превышен лимит контактов по вашему тарифу: {contact_limit}.'}, status=status.HTTP_400_BAD_REQUEST)
        # --- КОНЕЦ ОГРАНИЧЕНИЯ ---

        ser = ContactSerializer(data=request.data)
        if ser.is_valid():
            ser.save(contact_list=contact_list)
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['delete'], url_path='contacts/(?P<cid>[^/.]+)')
    def delete_contact(self, request, pk=None, cid=None):
        """
        DELETE /contactlists/{pk}/contacts/{cid}/
        """
        contact_list = self.get_object()
        contact = get_object_or_404(Contact, pk=cid, contact_list=contact_list)
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=['post'], url_path='import')
    def import_contacts(self, request, pk=None):
        """
        POST /contactlists/{pk}/import/ — импорт контактов из файла
        """
        contact_list = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'No file uploaded.'},
                            status=status.HTTP_400_BAD_REQUEST)

        emails = parse_emails(file_obj, file_obj.name)
        added = 0
        for email in emails:
            status_code = classify_email(email)
            obj, created = Contact.objects.get_or_create(
                contact_list=contact_list,
                email=email,
                defaults={'status': status_code}
            )
            if not created and obj.status != status_code:
                obj.status = status_code
                obj.save(update_fields=['status'])
            if created:
                added += 1

        return Response({'imported': added}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='export')
    def export_contacts(self, request, pk=None):
        """
        POST /contactlists/{pk}/export/ — экспорт контактов в файл
        """
        contact_list = self.get_object()
        format_type = request.data.get('format', 'txt')
        types = request.data.get('types', [])

        # Создаем ZIP архив для всех файлов
        import zipfile
        from io import BytesIO
        from django.core.files.base import ContentFile

        # Создаем буфер для ZIP файла
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Экспортируем каждый тип контактов в отдельный файл
            for contact_type in types:
                # Получаем контакты текущего типа
                contacts = Contact.objects.filter(
                    contact_list=contact_list,
                    status=contact_type
                ).values_list('email', flat=True).order_by('email')

                if contacts:
                    # Формируем содержимое файла в зависимости от формата
                    if format_type == 'txt':
                        content = '\n'.join(contacts)
                        content_type = 'text/plain'
                    elif format_type == 'csv':
                        content = 'email\n' + '\n'.join(contacts)
                        content_type = 'text/csv'
                    elif format_type == 'json':
                        content = json.dumps(list(contacts), indent=2)
                        content_type = 'application/json'
                    else:
                        return Response(
                            {'error': 'Unsupported format'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Создаем имя файла для текущего типа
                    type_names = {
                        'valid': 'действительные',
                        'invalid': 'недействительные',
                        'blacklist': 'черный_список'
                    }
                    filename = f'contacts_{contact_list.name}_{type_names[contact_type]}_{datetime.now().strftime("%Y-%m-%d")}.{format_type}'
                    
                    # Добавляем файл в ZIP архив
                    zip_file.writestr(filename, content)

        # Если нет контактов ни одного типа
        if zip_file.namelist() == []:
            return Response(
                {'error': 'No contacts found for selected types'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Подготавливаем ZIP файл для отправки
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="contacts_{contact_list.name}_{datetime.now().strftime("%Y-%m-%d")}.zip"'
        return response


class ListSpaView(LoginRequiredMixin, TemplateView):
    template_name = 'list.html'

