"""
Email Service for sending notifications.

Supports SMTP (Gmail) for sending appointment confirmations and notifications.
Falls back gracefully when SMTP credentials are not configured.
"""

import logging
from datetime import date, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service using SMTP for transactional emails."""

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send a plain text email."""
        settings = get_settings()

        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.info(f"[Demo Mode] Email to {to_email}: {subject}")
            logger.info(f"[Demo Mode] Body: {body[:200]}...")
            return True

        try:
            import aiosmtplib

            message = MIMEMultipart()
            message["From"] = settings.EMAIL_FROM
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "html"))

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_appointment_confirmation(
        self,
        to_email: str,
        patient_name: str,
        doctor_name: str,
        date: date,
        time: time,
        reason: str = "",
    ) -> bool:
        """Send a formatted appointment confirmation email."""
        subject = f"Appointment Confirmed - Dr. {doctor_name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #4F46E5; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">Appointment Confirmed ✓</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px;">
                <p>Dear <strong>{patient_name}</strong>,</p>
                <p>Your appointment has been successfully scheduled:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Doctor</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">Dr. {doctor_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Date</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{date.strftime('%B %d, %Y')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;"><strong>Time</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{time.strftime('%I:%M %p')}</td>
                    </tr>
                    {f'<tr><td style="padding: 8px;"><strong>Reason</strong></td><td style="padding: 8px;">{reason}</td></tr>' if reason else ''}
                </table>
                <p style="color: #6b7280; font-size: 14px;">
                    Please arrive 10 minutes before your scheduled time.<br>
                    If you need to cancel or reschedule, please do so at least 24 hours in advance.
                </p>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, body)

    async def send_doctor_report(
        self, to_email: str, doctor_name: str, report: str
    ) -> bool:
        """Send a summary report to a doctor."""
        subject = f"Daily Summary Report - Dr. {doctor_name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">Daily Summary Report</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px;">
                <p>Dear Dr. <strong>{doctor_name}</strong>,</p>
                <div>{report}</div>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, body)
