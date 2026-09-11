import phonenumbers
from phonenumbers import NumberParseException
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.exceptions import InvalidPhoneNumberError


class PhoneNumberMixin(BaseModel):
    phone_number: str

    @field_validator('phone_number')
    @classmethod
    def phone_number_validator(cls, v: str) -> str:
        # Пробуем распарсить номер как российский
        try:
            parsed_number = phonenumbers.parse(v, "RU")
        except NumberParseException:
            raise InvalidPhoneNumberError()
        # Проверяем, что номер валиден по правилам РФ
        if not phonenumbers.is_valid_number(parsed_number):
            raise InvalidPhoneNumberError()

        # Возвращаем номер в международном формате (+7...)
        return phonenumbers.format_number(
            parsed_number,
            phonenumbers.PhoneNumberFormat.E164
        )


class RegisterSchema(PhoneNumberMixin):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginEmailSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginPhoneNumberSchema(PhoneNumberMixin):
    password: str = Field(min_length=8, max_length=128)


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "Bearer"
