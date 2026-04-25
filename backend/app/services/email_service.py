"""
Сервис отправки email уведомлений
"""
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from loguru import logger

from ..config import get_settings
from ..models.reminder import Reminder

settings = get_settings()


class EmailService:
    """Сервис для отправки email уведомлений"""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Отправить email.
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            body_html: HTML содержимое
            body_text: Текстовое содержимое (fallback)
        
        Returns:
            True если отправлено успешно
        """
        if not self.user or not self.password:
            logger.warning("SMTP не настроен, email не отправлен")
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email
            
            # Текстовая версия
            if body_text:
                text_part = MIMEText(body_text, "plain", "utf-8")
                message.attach(text_part)
            
            # HTML версия
            html_part = MIMEText(body_html, "html", "utf-8")
            message.attach(html_part)
            
            # Отправка
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=True
            )
            
            logger.info(f"Email отправлен на {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False
    
    async def send_reminder_notification(
        self,
        to_email: str,
        reminder: Reminder
    ) -> bool:
        """Отправить уведомление о напоминании"""
        amount_text = f"{reminder.amount:.2f} {reminder.currency}" if reminder.amount else "сумма не указана"
        
        subject = f"💰 Напоминание: {reminder.title}"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px 10px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .amount {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1f2937;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #6b7280;
                    font-size: 12px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>💰 Напоминание об оплате</h1>
            </div>
            <div class="content">
                <h2>{reminder.title}</h2>
                {f'<p>{reminder.description}</p>' if reminder.description else ''}
                <div class="amount">
                    Сумма: {amount_text}
                </div>
                <p>Это автоматическое напоминание от вашего финансового помощника.</p>
            </div>
            <div class="footer">
                <p>Finance App — Управление личными финансами</p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Напоминание об оплате: {reminder.title}
        
        {reminder.description or ''}
        
        Сумма: {amount_text}
        
        ---
        Finance App — Управление личными финансами
        """
        
        return await self.send_email(to_email, subject, body_html, body_text)
    
    async def send_suspicious_alert(
        self,
        to_email: str,
        transactions: List[dict]
    ) -> bool:
        """Отправить уведомление о подозрительных транзакциях"""
        subject = "⚠️ Обнаружены подозрительные транзакции"
        
        transactions_html = ""
        for tx in transactions:
            transactions_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                    {tx.get('description', 'Без описания')}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                    {tx.get('amount', 0):.2f} ₽
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                    {tx.get('reason', '')}
                </td>
            </tr>
            """
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1 style="color: #dc2626;">⚠️ Подозрительные транзакции</h1>
            <p>В вашем аккаунте обнаружены подозрительные транзакции:</p>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f3f4f6;">
                        <th style="padding: 10px; text-align: left;">Описание</th>
                        <th style="padding: 10px; text-align: right;">Сумма</th>
                        <th style="padding: 10px; text-align: left;">Причина</th>
                    </tr>
                </thead>
                <tbody>
                    {transactions_html}
                </tbody>
            </table>
            <p style="margin-top: 20px;">
                Пожалуйста, проверьте эти транзакции в приложении.
            </p>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, body_html)


# Глобальный экземпляр
email_service = EmailService()


def get_email_service() -> EmailService:
    """Получить экземпляр сервиса email"""
    return email_service
