from fastapi import APIRouter, Depends, Response, Request, status, HTTPException

from app.api.dependencies import get_auth_service, get_current_user, require_roles
from app.core.config import settings
from app.db.models import User
from app.enums import UserRole
from app.schemas import UserRead, UserRoleUpdate, RegisterSchema, TokenResponseSchema, LoginEmailSchema, LoginPhoneNumberSchema
from app.services import AuthService

router = APIRouter(
    prefix="/auth",
)


@router.post("/register", response_model=UserRead)
async def register_user(
        register_data: RegisterSchema,
        auth_service: AuthService = Depends(get_auth_service)
) -> UserRead:
    return await auth_service.register(register_data)


@router.post("/login/email", response_model=TokenResponseSchema)
async def login_with_email(
        response: Response,
        login_email_data: LoginEmailSchema,
        auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponseSchema:
    tokens = await auth_service.login_email(login_email_data)
    response.set_cookie(
        key=settings.refresh_token_cookies.key,
        value=tokens["refresh_token"],
        secure=settings.refresh_token_cookies.secure,
        samesite=settings.refresh_token_cookies.same_site,
        httponly=settings.refresh_token_cookies.httponly,
    )
    return TokenResponseSchema(
        access_token=tokens["access_token"],
    )


@router.post("/login/phone_number", response_model=TokenResponseSchema)
async def login_with_phone_number(
        response: Response,
        login_phone_number_data: LoginPhoneNumberSchema,
        auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponseSchema:
    tokens = await auth_service.login_phone_number(login_phone_number_data)
    response.set_cookie(
        key=settings.refresh_token_cookies.key,
        value=tokens["refresh_token"],
        secure=settings.refresh_token_cookies.secure,
        samesite=settings.refresh_token_cookies.same_site,
        httponly=settings.refresh_token_cookies.httponly,
    )
    return TokenResponseSchema(
        access_token=tokens["access_token"],
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
        request: Request,
        response: Response,
        auth_service: AuthService = Depends(get_auth_service)
) -> None:
    refresh_token = request.cookies.get(settings.refresh_token_cookies.key, None)

    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing in cookies",
        )

    await auth_service.logout(refresh_token)
    response.delete_cookie(settings.refresh_token_cookies.key)


@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_tokens(
        request: Request,
        response: Response,
        auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponseSchema:
    refresh_token = request.cookies.get(settings.refresh_token_cookies.key)
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing in cookies",
        )

    tokens = await auth_service.refresh_tokens(refresh_token)
    response.set_cookie(
        key=settings.refresh_token_cookies.key,
        value=tokens["refresh_token"],
        secure=settings.refresh_token_cookies.secure,
        samesite=settings.refresh_token_cookies.same_site,
        httponly=settings.refresh_token_cookies.httponly,
    )
    return TokenResponseSchema(access_token=tokens["access_token"])


@router.post("/logout/all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
        current_user: User = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
) -> None:
    await auth_service.logout_all(current_user.id)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
        current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
        user_id: str,
        role_data: UserRoleUpdate,
        _: User = Depends(require_roles(UserRole.ADMIN)),
        auth_service: AuthService = Depends(get_auth_service),
) -> UserRead:
    return await auth_service.update_user_role(user_id, role_data.role)
