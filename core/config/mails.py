from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Environment, FileSystemLoader
from core.app.env import settings,BASE_DIR
from datetime import datetime
template_dir = BASE_DIR / "core/templates"
env = Environment(loader=FileSystemLoader(template_dir))


conf = ConnectionConfig(

    MAIL_USERNAME=settings.SMTP_USERNAME,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>",
    
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOSTNAME,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def send_welcome_mail(email_to: str, user_name: str):
    template = env.get_template("welcome_email.html")
    html_content = template.render(
        company_name=settings.APP_NAME,
        current_year=datetime.now().year,
        company_address=settings.MAIL_FROM_EMAIL,
        user_name=user_name,
    )
    message = MessageSchema(
        subject="Wellcome",
        recipients=[email_to],
        body=html_content,
        subtype="html",
        from_email=f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
    )
    fm = FastMail(config=conf)
    await fm.send_message(message=message)

async def send_forgot_password_mail(email_to: str,reset_url:str):
    template = env.get_template("forgot_password.html")
    html_content = template.render(
        company_name=settings.APP_NAME,
        current_year=datetime.now().year,
        company_address=settings.MAIL_FROM_EMAIL,
        email=email_to,
        reset_link=reset_url,
    )
    print(email_to)
    message = MessageSchema(
        subject="Reset Password",
        recipients=[email_to],
        body=html_content,
        subtype="html",
        from_email=f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
    )
    fm = FastMail(config=conf)
    await fm.send_message(message=message)


async def send_signup_otp_mail(email_to: str, otp_code: str, expiry_minutes: str):
  template = env.get_template("signup-otp-mail.html")
  html_content = template.render(
    company_name=settings.APP_NAME,
    otp_code=otp_code,
    expiry_minutes=expiry_minutes,
    email=email_to,
  )
  message = MessageSchema(
    subject="Reset Password",
    recipients=[email_to],
    body=html_content,
    subtype="html",
    from_email=f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM_EMAIL}>"
  )
  fm = FastMail(config=conf)
  await fm.send_message(message=message)

