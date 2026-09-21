"""
router.py - Thin HTTP route handlers for Authentication domain.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from langfuse import observe

from backend.database.connection import get_db
from backend.auth.dependencies import ClerkUser
from backend.auth.schemas import (
    UserAuthResponse,
    UserInfoResponse,
    FaceDescriptorResponse,
    FaceRegisterRequest,
    FaceLoginRequest,
    FaceUpdateRequest,
    MessageResponse,
    AccountDeletionResponse,
)
from backend.auth import service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/me",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch current Clerk user information and face status",
)
@observe()
def get_current_user_info(
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> UserInfoResponse:
    return service.get_current_user_info(
        clerk_user_id=clerk_user.get("user_id"),
        db=db,
    )


@router.get(
    "/user/{identifier}",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch user information and face login availability status by Clerk user ID",
)
@observe()
def get_user_info(
    identifier: str,
    db: Session = Depends(get_db),
) -> UserInfoResponse:
    return service.get_user_info_by_identifier(
        identifier=identifier,
        db=db,
    )


@router.get(
    "/faces",
    response_model=List[FaceDescriptorResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered faces for current user",
)
@observe()
def list_user_faces(
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> List[FaceDescriptorResponse]:
    return service.list_user_faces(
        clerk_user_id=clerk_user.get("user_id"),
        db=db,
    )


@router.delete(
    "/faces/{face_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a specific registered face",
)
@observe()
def delete_face(
    face_id: int,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    return service.delete_user_face(
        face_id=face_id,
        clerk_user_id=clerk_user.get("user_id"),
        db=db,
    )


@router.post(
    "/register-face",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a new facial descriptor for authenticated user",
)
@observe()
def register_face(
    payload: FaceRegisterRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    return service.register_user_face(
        clerk_user_id=clerk_user.get("user_id"),
        face_descriptor=payload.face_descriptor,
        label=payload.label,
        db=db,
    )


@router.post(
    "/add-face",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Add an additional face biometric descriptor for authenticated user",
)
@observe()
def add_face(
    payload: FaceUpdateRequest,
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> MessageResponse:
    return service.add_user_face(
        clerk_user_id=clerk_user.get("user_id"),
        face_descriptor=payload.face_descriptor,
        label=payload.label,
        db=db,
    )


@router.post(
    "/login/face",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user using biometric facial recognition",
)
@observe()
def login_face(
    payload: FaceLoginRequest,
    db: Session = Depends(get_db),
) -> UserAuthResponse:
    return service.login_user_by_face(
        face_descriptor=payload.face_descriptor,
        db=db,
    )


@router.delete(
    "/account",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete user account, local data, and Clerk account",
)
@observe()
def delete_account(
    clerk_user: dict = ClerkUser,
    db: Session = Depends(get_db),
) -> AccountDeletionResponse:
    return service.delete_user_account(
        clerk_user_id=clerk_user.get("user_id"),
        db=db,
    )
