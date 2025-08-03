import hashlib
import hmac
import json
import requests
from django.conf import settings
from django.utils import timezone
from .models import CloudPaymentsTransaction, BillingSettings, PurchasedPlan


class CloudPaymentsService:
    """Сервис для работы с CloudPayments"""
    
    def __init__(self):
        self.settings = BillingSettings.get_settings()
        self.public_id = self.settings.cloudpayments_public_id
        self.api_secret = self.settings.cloudpayments_api_secret
        self.test_mode = self.settings.cloudpayments_test_mode
        
        if self.test_mode:
            self.base_url = "https://api.cloudpayments.ru/test"
        else:
            self.base_url = "https://api.cloudpayments.ru"
    
    def create_payment(self, user, plan, amount=None, description=None):
        """
        Создать платеж в CloudPayments
        
        Args:
            user: Пользователь
            plan: Тарифный план
            amount: Сумма (если не указана, берется из плана)
            description: Описание платежа
        
        Returns:
            dict: Данные для создания платежа
        """
        if amount is None:
            amount = float(plan.get_final_price())
        
        if description is None:
            description = f"Тариф {plan.title} - {plan.get_final_price()}₽"
        
        # Создаем запись транзакции
        transaction = CloudPaymentsTransaction.objects.create(
            user=user,
            plan=plan,
            amount=amount,
            description=description,
            status=CloudPaymentsTransaction.STATUS_PENDING
        )
        
        # Формируем данные для CloudPayments
        payment_data = {
            "PublicId": self.public_id,
            "Amount": amount,
            "Currency": "RUB",
            "Description": description,
            "AccountId": str(user.id),
            "Email": user.email,
            "JsonData": {
                "transaction_id": transaction.id,
                "plan_id": plan.id,
                "user_id": user.id
            }
        }
        
        return {
            "transaction_id": transaction.id,
            "cloudpayments_id": transaction.cloudpayments_id,
            "amount": amount,
            "description": description,
            "payment_data": payment_data
        }
    
    def verify_signature(self, data, signature):
        """
        Проверить подпись от CloudPayments
        
        Args:
            data: Данные запроса
            signature: Подпись
        
        Returns:
            bool: True если подпись верна
        """
        # Создаем строку для подписи
        sign_string = ""
        for key in sorted(data.keys()):
            if key != "Signature":
                sign_string += str(data[key]) + ";"
        
        # Убираем последний символ ";"
        sign_string = sign_string[:-1]
        
        # Создаем подпись
        expected_signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def process_webhook(self, data, signature):
        """
        Обработать webhook от CloudPayments
        
        Args:
            data: Данные webhook
            signature: Подпись
        
        Returns:
            dict: Результат обработки
        """
        # Проверяем подпись
        if not self.verify_signature(data, signature):
            return {"success": False, "error": "Invalid signature"}
        
        try:
            # Получаем транзакцию
            transaction_id = data.get("TransactionId")
            transaction = CloudPaymentsTransaction.objects.get(
                cloudpayments_id=transaction_id
            )
            
            # Обновляем данные транзакции
            transaction.amount = float(data.get("Amount", 0))
            transaction.payment_method = data.get("PaymentMethod", "")
            transaction.card_last_four = data.get("CardLastFour", "")
            transaction.card_type = data.get("CardType", "")
            transaction.ip_address = data.get("IpAddress", "")
            transaction.user_agent = data.get("UserAgent", "")
            
            # Обрабатываем статус
            status = data.get("Status")
            if status == "Completed":
                transaction.mark_as_completed()
                self._activate_plan(transaction)
            elif status == "Failed":
                transaction.mark_as_failed()
            elif status == "Cancelled":
                transaction.status = CloudPaymentsTransaction.STATUS_CANCELLED
                transaction.save(update_fields=['status'])
            
            return {"success": True, "transaction_id": transaction.id}
            
        except CloudPaymentsTransaction.DoesNotExist:
            return {"success": False, "error": "Transaction not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _activate_plan(self, transaction):
        """
        Активировать тариф после успешной оплаты
        
        Args:
            transaction: Транзакция CloudPayments
        """
        user = transaction.user
        plan = transaction.plan
        
        # Создаем купленный тариф
        purchased_plan = PurchasedPlan.objects.create(
            user=user,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),  # 30 дней
            is_active=True,
            payment_method="cloudpayments",
            transaction_id=transaction.cloudpayments_id,
            amount_paid=transaction.amount
        )
        
        # Обновляем текущий план пользователя
        user.current_plan = plan
        user.plan_expiry = purchased_plan.end_date
        user.save(update_fields=['current_plan', 'plan_expiry'])
    
    def get_transaction_status(self, transaction_id):
        """
        Получить статус транзакции из CloudPayments
        
        Args:
            transaction_id: ID транзакции в CloudPayments
        
        Returns:
            dict: Статус транзакции
        """
        url = f"{self.base_url}/payments/get"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_secret}"
        }
        data = {
            "TransactionId": transaction_id
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def refund_transaction(self, transaction_id, amount=None):
        """
        Возврат средств
        
        Args:
            transaction_id: ID транзакции в CloudPayments
            amount: Сумма возврата (если не указана, возвращается вся сумма)
        
        Returns:
            dict: Результат возврата
        """
        url = f"{self.base_url}/payments/refund"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_secret}"
        }
        data = {
            "TransactionId": transaction_id
        }
        
        if amount:
            data["Amount"] = amount
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def create_recurring_payment(self, user, plan, token):
        """
        Создать рекуррентный платеж
        
        Args:
            user: Пользователь
            plan: Тарифный план
            token: Токен карты
        
        Returns:
            dict: Результат создания рекуррентного платежа
        """
        url = f"{self.base_url}/payments/tokens/charge"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_secret}"
        }
        
        data = {
            "Token": token,
            "Amount": float(plan.get_final_price()),
            "Currency": "RUB",
            "AccountId": str(user.id),
            "Description": f"Автопродление тарифа {plan.title}"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}


# Глобальный экземпляр сервиса
cloudpayments_service = CloudPaymentsService() 