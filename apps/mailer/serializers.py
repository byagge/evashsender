# mailer/serializers.py

from rest_framework import serializers
from .models import ContactList, Contact

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'email', 'status', 'added_date']
    
    def validate_email(self, value):
        """Валидация email адреса при ручном добавлении"""
        from .utils import is_syntax_valid, is_reserved_domain, is_disposable_domain
        
        # Приводим к нижнему регистру
        email = value.lower().strip()
        
        # Базовая проверка синтаксиса
        syntax_valid = is_syntax_valid(email)
        if not syntax_valid:
            raise serializers.ValidationError('Неверный синтаксис email адреса')
        
        try:
            domain = email.split('@', 1)[1].lower()
        except (ValueError, IndexError) as e:
            raise serializers.ValidationError('Не удалось извлечь домен')
        
        # Проверка зарезервированных доменов
        is_reserved = is_reserved_domain(domain)
        if is_reserved:
            raise serializers.ValidationError('Зарезервированный домен')
        
        # Проверка disposable доменов (предупреждение, но не ошибка)
        is_disposable = is_disposable_domain(domain)
        if is_disposable:
            # Добавляем предупреждение, но не блокируем
            pass
        
        # Возвращаем очищенный email
        return email
    
    def validate(self, data):
        """Дополнительная валидация при ручном добавлении"""
        from .utils import is_disposable_domain
        
        email = data.get('email', '')
        if email:
            try:
                domain = email.split('@', 1)[1].lower()
                
                # Устанавливаем статус на основе проверок
                if is_disposable_domain(domain):
                    data['status'] = Contact.BLACKLIST
                else:
                    data['status'] = Contact.VALID
                    
            except (ValueError, IndexError) as e:
                data['status'] = Contact.INVALID
        else:
            pass
        
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
