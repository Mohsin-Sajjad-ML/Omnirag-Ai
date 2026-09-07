"""
auth.py - Authentication route handlers.

Defines API endpoints under the '/auth' prefix:
- POST /auth/register: Registers a new user account.
- POST /auth/login/password: Authenticates user via password.
- GET /auth/user/{username}: Checks user account and face registration status.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserAuthResponse,
    UserInfoResponse,
    FaceRegisterRequest,
    FaceLoginRequest,
    FaceUpdateRequest,
    MessageResponse,
)
from app.security import hash_password, verify_password
from app.face_utils import find_best_face_match, DEFAULT_FACE_MATCH_THRESHOLD

# Initialize router under '/auth' prefix
router = APIRouter(prefix="/auth", tags=["Authentication"])



@router.post(
    "/register",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a new user account"
)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new user account.
    - Validates input format (username 3-30 chars alphanumeric+underscore, password min 6 chars).
    - Checks for existing duplicate usernames (returns 400 Bad Request if taken).
    - Hashes password using bcrypt prior to database storage.
    - Returns success response without exposing password or hash.
    """
    # Query database for existing username
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Securely hash user password
    hashed_pwd = hash_password(payload.password)

    # Construct new User record
    new_user = User(
        username=payload.username,
        hashed_password=hashed_pwd
    )

    # Save user to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserAuthResponse(
        username=new_user.username,
        message="User registered successfully"
    )


@router.post(
    "/login/password",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user via password"
)
def login_password(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user using username and password.
    - Verifies user exists in database.
    - Compares plain-text password against stored bcrypt hash.
    - Returns 401 Unauthorized with generic error message for invalid credentials
      (prevents username enumeration attacks).
    """
    user = db.query(User).filter(User.username == payload.username).first()

    # Generic exception used for both missing user and wrong password
    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password"
    )

    if not user:
        raise invalid_credentials_error

    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials_error

    return UserAuthResponse(
        username=user.username,
        message="Login successful"
    )


@router.get(
    "/user/{username}",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch user information and face login availability status"
)
def get_user_info(username: str, db: Session = Depends(get_db)):
    """
    Checks if a user exists and returns account metadata.
    - Used by frontend login screen to determine if facial recognition login is available.
    - Returns 404 Not Found if username does not exist.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    has_face = user.face_descriptor is not None and len(user.face_descriptor.strip()) > 0

    return UserInfoResponse(
        username=user.username,
        created_at=user.created_at,
        has_face_registered=has_face
    )


@router.post(
    "/register-face",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Register facial descriptor for existing user"
)
def register_face(payload: FaceRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a 128-dimensional facial embedding for a registered user.
    - Finds the user by username.
    - Serializes the float array into a JSON string and stores it in face_descriptor column.
    - Returns 404 if user does not exist.
    - Returns 200 OK with success confirmation.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.face_descriptor = json.dumps(payload.face_descriptor)
    db.commit()
    db.refresh(user)

    return MessageResponse(message="Face registered successfully")


@router.post(
    "/login/face",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user using biometric facial recognition"
)
def login_face(payload: FaceLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user via webcam face capture:
    - Loads all users with a registered face_descriptor in the database.
    - Computes Euclidean distance between incoming descriptor and all stored descriptors.
    - Threshold note: 0.5 is a reasonable starting threshold and may need tuning
      based on testing across different lighting and camera environments.
    - Matches the closest user if the minimum distance < 0.5.
    - Returns 401 Unauthorized with 'Face not recognized' if no match meets threshold.
    """
    # Query all users with an existing face descriptor
    users_with_face = db.query(User).filter(User.face_descriptor.isnot(None)).all()

    # Parse stored JSON descriptors into candidate tuples (username, descriptor_list)
    candidate_users = []
    for user in users_with_face:
        if user.face_descriptor and user.face_descriptor.strip():
            try:
                descriptor = json.loads(user.face_descriptor)
                if isinstance(descriptor, list):
                    candidate_users.append((user.username, descriptor))
            except (json.JSONDecodeError, ValueError):
                continue

    # Isolated matching function evaluates Euclidean distances against threshold (0.5)
    match_result = find_best_face_match(
        incoming_descriptor=payload.face_descriptor,
        candidate_users=candidate_users,
        threshold=DEFAULT_FACE_MATCH_THRESHOLD
    )

    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face not recognized"
        )

    matched_username, match_distance = match_result

    return UserAuthResponse(
        username=matched_username,
        message="Login successful"
    )


@router.post(
    "/add-face",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update face biometric descriptor with password verification"
)
def add_face(payload: FaceUpdateRequest, db: Session = Depends(get_db)):
    """
    Updates or re-registers a user's face descriptor from an authenticated/account view.
    - Validates user exists.
    - Verifies account password before allowing biometric data overwrite.
    - Serializes and saves new face descriptor.
    - Returns 200 OK with success confirmation.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Require correct password confirmation prior to updating biometric records
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    user.face_descriptor = json.dumps(payload.face_descriptor)
    db.commit()
    db.refresh(user)

    return MessageResponse(message="Face updated successfully")

