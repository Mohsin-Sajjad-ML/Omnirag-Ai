"""
service.py - Business logic for Authentication, User Profile, Face Biometrics, and Account Management.
"""
from langfuse import observe


import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from clerk_backend_api import Clerk

from backend.database.models import User, FaceDescriptor, Document, ChatSession, ChatMessage
from backend.auth.schemas import (
    UserAuthResponse,
    UserInfoResponse,
    FaceDescriptorResponse,
    MessageResponse,
    AccountDeletionResponse,
)
from backend.auth.face_matching import find_best_face_match, DEFAULT_FACE_MATCH_THRESHOLD
from backend.documents.rag_service import delete_user_collection
from backend.config import settings

logger = logging.getLogger(__name__)


@observe()
def get_current_user_info(clerk_user_id: str, db: Session) -> UserInfoResponse:
    """
    Returns account and face registration status for the currently authenticated Clerk user.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    face_count = db.query(FaceDescriptor).filter(FaceDescriptor.clerk_user_id == clerk_user_id).count()

    if not user:
        return UserInfoResponse(
            clerk_user_id=clerk_user_id,
            username=clerk_user_id,
            created_at=datetime.now(timezone.utc),
            has_face_registered=face_count > 0,
            face_count=face_count,
        )

    return UserInfoResponse(
        clerk_user_id=user.clerk_user_id,
        username=user.clerk_user_id,
        created_at=user.created_at,
        has_face_registered=face_count > 0,
        face_count=face_count,
    )


@observe()
def get_user_info_by_identifier(identifier: str, db: Session) -> UserInfoResponse:
    """
    Checks if a user exists and returns account metadata by identifier (clerk_user_id).
    """
    user = db.query(User).filter(User.clerk_user_id == identifier).first()
    face_count = db.query(FaceDescriptor).filter(FaceDescriptor.clerk_user_id == identifier).count()

    if not user and face_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserInfoResponse(
        clerk_user_id=user.clerk_user_id if user else identifier,
        username=user.clerk_user_id if user else identifier,
        created_at=user.created_at if user else datetime.now(timezone.utc),
        has_face_registered=face_count > 0,
        face_count=face_count,
    )


@observe()
def list_user_faces(clerk_user_id: str, db: Session) -> List[FaceDescriptorResponse]:
    """
    Returns the currently signed-in user's list of registered faces without raw embeddings.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    faces = (
        db.query(FaceDescriptor)
        .filter(FaceDescriptor.clerk_user_id == clerk_user_id)
        .order_by(FaceDescriptor.created_at.desc())
        .all()
    )
    return [
        FaceDescriptorResponse(
            id=f.id,
            label=f.label,
            created_at=f.created_at,
        )
        for f in faces
    ]


@observe()
def delete_user_face(face_id: int, clerk_user_id: str, db: Session) -> MessageResponse:
    """
    Deletes a specific face registration belonging to the currently authenticated Clerk user.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    face = db.query(FaceDescriptor).filter(FaceDescriptor.id == face_id).first()
    if not face:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Face registration not found."
        )

    if face.clerk_user_id != clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this face registration."
        )

    db.delete(face)
    db.commit()

    return MessageResponse(message="Face deleted successfully")


@observe()
def register_user_face(
    clerk_user_id: str,
    face_descriptor: List[float],
    label: Optional[str],
    db: Session,
) -> MessageResponse:
    """
    Registers a new 128-dimensional facial embedding row for the authenticated Clerk user.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        user = User(clerk_user_id=clerk_user_id)
        db.add(user)
        db.flush()

    existing_count = db.query(FaceDescriptor).filter(FaceDescriptor.clerk_user_id == clerk_user_id).count()
    default_label = f"Face {existing_count + 1}"
    resolved_label = (label or "").strip() or default_label

    new_face = FaceDescriptor(
        clerk_user_id=clerk_user_id,
        descriptor=json.dumps(face_descriptor),
        label=resolved_label,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_face)
    db.commit()
    db.refresh(new_face)

    return MessageResponse(message="Face registered successfully")


@observe()
def add_user_face(
    clerk_user_id: str,
    face_descriptor: List[float],
    label: Optional[str],
    db: Session,
) -> MessageResponse:
    """
    Adds an additional face biometric descriptor for the authenticated Clerk user.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        user = User(clerk_user_id=clerk_user_id)
        db.add(user)
        db.flush()

    existing_count = db.query(FaceDescriptor).filter(FaceDescriptor.clerk_user_id == clerk_user_id).count()
    default_label = f"Face {existing_count + 1}"
    resolved_label = (label or "").strip() or default_label

    new_face = FaceDescriptor(
        clerk_user_id=clerk_user_id,
        descriptor=json.dumps(face_descriptor),
        label=resolved_label,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_face)
    db.commit()
    db.refresh(new_face)

    return MessageResponse(message="Face added successfully")


@observe()
def login_user_by_face(face_descriptor: List[float], db: Session) -> UserAuthResponse:
    """
    Authenticates a user via webcam face capture:
    - Compares incoming descriptor against ALL FaceDescriptor rows across ALL users.
    - Finds closest match below distance threshold (0.5).
    - Generates a Clerk sign-in ticket token.
    """
    all_face_records = db.query(FaceDescriptor).all()

    candidate_users = []
    for face in all_face_records:
        if face.descriptor and face.descriptor.strip():
            try:
                descriptor = json.loads(face.descriptor)
                if isinstance(descriptor, list):
                    candidate_users.append((face.clerk_user_id, descriptor))
            except (json.JSONDecodeError, ValueError):
                continue

    match_result = find_best_face_match(
        incoming_descriptor=face_descriptor,
        candidate_users=candidate_users,
        threshold=DEFAULT_FACE_MATCH_THRESHOLD,
    )

    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face not recognized"
        )

    matched_clerk_user_id, _ = match_result

    sign_in_token = None
    secret_key = settings.CLERK_SECRET_KEY
    if secret_key:
        try:
            import backend.auth
            clerk_cls = getattr(backend.auth, "Clerk", Clerk)
            clerk = clerk_cls(bearer_auth=secret_key)
            sign_in_token_res = clerk.sign_in_tokens.create(
                request={"user_id": matched_clerk_user_id}
            )
            if hasattr(sign_in_token_res, "token") and sign_in_token_res.token:
                sign_in_token = sign_in_token_res.token
            elif isinstance(sign_in_token_res, dict):
                sign_in_token = sign_in_token_res.get("token")
        except Exception as e:
            logger.warning(f"Could not generate Clerk sign-in token for {matched_clerk_user_id}: {e}")

    return UserAuthResponse(
        clerk_user_id=matched_clerk_user_id,
        username=matched_clerk_user_id,
        sign_in_token=sign_in_token,
        message="Login successful"
    )


@observe()
def delete_user_account(clerk_user_id: str, db: Session) -> AccountDeletionResponse:
    """
    Destructive operation that deletes all local user data and the remote Clerk user.
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session token does not identify a user."
        )

    logger.warning("Starting destructive account deletion for Clerk user: %s", clerk_user_id)

    # 1. Delete all FaceDescriptor records
    deleted_faces_count = (
        db.query(FaceDescriptor)
        .filter(FaceDescriptor.clerk_user_id == clerk_user_id)
        .delete(synchronize_session=False)
    )

    # 2. Delete all Document records and purge ChromaDB collection
    deleted_documents_count = (
        db.query(Document)
        .filter(Document.clerk_user_id == clerk_user_id)
        .delete(synchronize_session=False)
    )
    delete_user_collection(clerk_user_id=clerk_user_id)

    # 3. Delete all ChatMessages and ChatSessions
    sessions = db.query(ChatSession).filter(ChatSession.clerk_user_id == clerk_user_id).all()
    session_ids = [s.id for s in sessions]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(synchronize_session=False)
    deleted_sessions_count = (
        db.query(ChatSession)
        .filter(ChatSession.clerk_user_id == clerk_user_id)
        .delete(synchronize_session=False)
    )

    # 4. Delete local User table row
    db.query(User).filter(User.clerk_user_id == clerk_user_id).delete(synchronize_session=False)

    # Commit local database deletions
    db.commit()

    # 5. Delete user from Clerk via Backend SDK
    secret_key = settings.CLERK_SECRET_KEY
    if secret_key:
        try:
            import backend.auth
            clerk_cls = getattr(backend.auth, "Clerk", Clerk)
            clerk = clerk_cls(bearer_auth=secret_key)
            clerk.users.delete(user_id=clerk_user_id)
            logger.info("Successfully deleted user %s from Clerk.", clerk_user_id)
        except Exception as exc:
            logger.error("Failed to delete user %s from Clerk: %s", clerk_user_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Local data deleted, but failed to delete user from Clerk: {exc}",
            )
    else:
        logger.warning("CLERK_SECRET_KEY not set; skipped remote Clerk user deletion.")

    return AccountDeletionResponse(
        message="Account and all associated data deleted successfully.",
        clerk_user_id=clerk_user_id,
        deleted_faces_count=deleted_faces_count,
        deleted_documents_count=deleted_documents_count,
        deleted_sessions_count=deleted_sessions_count,
    )
