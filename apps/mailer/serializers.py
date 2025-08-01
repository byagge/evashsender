# mailer/serializers.py

from rest_framework import serializers
from .models import ContactList, Contact

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'email', 'status', 'added_date']
    
    def validate_email(self, value):
        """Валидация email адреса при ручном добавлении"""
        from .utils import validate_email_production
        
        # Приводим к нижнему регистру
        email = value.lower().strip()
        
        # Проверяем email с полной продакшен-валидацией (включая SMTP)
        validation_result = validate_email_production(email)
        
        if not validation_result['is_valid']:
            # Формируем понятное сообщение об ошибке
            if validation_result['errors']:
                error_msg = '; '.join(validation_result['errors'])
            else:
                error_msg = 'Email адрес не прошел валидацию'
            raise serializers.ValidationError(error_msg)
        
        # Возвращаем очищенный email
        return email
    
    def validate(self, data):
        """Дополнительная валидация при ручном добавлении"""
        from .utils import validate_email_production
        
        email = data.get('email', '')
        if email:
            validation_result = validate_email_production(email)
            
            # Устанавливаем правильный статус на основе валидации
            if validation_result['is_valid']:
                data['status'] = validation_result['status']
            else:
                data['status'] = Contact.INVALID
            
            # Добавляем предупреждения в контекст, если есть
            if validation_result.get('warnings'):
                data['warnings'] = validation_result['warnings']
        
        return data

class ContactListSerializer(serializers.ModelSerializer):
    # убираем source=… — DRF найдёт total_contacts, valid_count и т.д. по name
    total_contacts    = serializers.IntegerField(read_only=True)
    valid_count       = serializers.IntegerField(read_only=True)
    invalid_count     = serializers.IntegerField(read_only=True)
    blacklisted_count = serializers.IntegerField(read_only=True)
    contacts          = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = ContactList
        fields = [
            'id', 'name', 'created_at', 'updated_at',
            'total_contacts', 'valid_count', 'invalid_count', 'blacklisted_count',
            'contacts',
        ]
