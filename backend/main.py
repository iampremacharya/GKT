from pathlib import Path
import hashlib
import io
import json
import math
import os
import secrets
import shutil
import smtplib
import uuid

from PIL import Image, UnidentifiedImageError

from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends
)

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text as sql_text

from database import (
    initialize_database,

    create_user,
    get_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_username_or_email,

    get_discoverable_users,
    get_all_users,
    embedding_from_row,

    update_user_profile,
    delete_user,

    create_swipe_once,
    get_user_swipes,
    is_mutual_match,
    get_matches,

    create_password_reset_token,
    cleanup_expired_reset_tokens,
    reset_password_with_token,
    engine
)


from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_user,
    security
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR = STORAGE_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Find Your 7 Twins API",
    description="Visual twin discovery social network API",
    version="3.1.0"
)


def _csv_env(name: str, default: str = ""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


ALLOWED_ORIGINS = _csv_env("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "https://gkt.com.np"))
if os.getenv("ALLOW_DEV_ORIGINS", "false").lower() == "true":
    ALLOWED_ORIGINS.extend([
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ])


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


initialize_database()


# ============================================================
# PASSWORD RESET CONFIG
# ============================================================

RESET_TOKEN_MINUTES = 20

FRONTEND_RESET_URL = os.getenv(
    "FRONTEND_RESET_URL",
    os.getenv("RESET_URL", "https://gkt.com.np/twins/")
)

DEV_RESET_MODE = (
    os.getenv("DEV_RESET_MODE", "false").lower() == "true"
)


# ============================================================
# SMTP CONFIGURATION
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    ""
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587"
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    ""
)

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    ""
)

SMTP_FROM = os.getenv(
    "SMTP_FROM",
    ""
)


# ============================================================
# HELPERS
# ============================================================

def save_upload(upload: UploadFile):
    extension = Path(upload.filename or "").suffix.lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_types = {"image/jpeg", "image/png", "image/webp"}

    if extension not in allowed_extensions or (upload.content_type and upload.content_type not in allowed_types):
        raise HTTPException(status_code=400, detail="Please upload a JPG, JPEG, PNG or WEBP image.")

    max_bytes = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    data = upload.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Image is too large. The maximum upload size is 10 MB.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.")

    filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return filename, str(destination)


def public_user(row, include_email: bool = False):
    user = {
        "id": row["id"],
        "username": row["username"],
        "name": row["name"],
        "country": row["country"],
        "photo_url": f"/api/photos/{row['photo_path']}",
        "discoverable": bool(row["discoverable"]),
        "created_at": row["created_at"],
    }
    if include_email:
        user["email"] = row["email"]
    return user


def cosine_similarity(a, b):
    if len(a) != len(b) or not a:
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for x, y in zip(a, b):
        try:
            x = float(x)
            y = float(y)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(x) or not math.isfinite(y):
            return 0.0
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    denominator = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denominator == 0.0:
        return 0.0
    return float(dot / denominator)


def parse_embedding(raw_embedding: str):
    try:
        embedding = json.loads(raw_embedding)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid face embedding.")

    if not isinstance(embedding, list) or len(embedding) != 128:
        raise HTTPException(status_code=400, detail="Invalid face embedding. Please use a supported face photo.")

    cleaned = []
    for value in embedding:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid face embedding.")
        if not math.isfinite(number):
            raise HTTPException(status_code=400, detail="Invalid face embedding.")
        cleaned.append(number)

    if math.sqrt(sum(value * value for value in cleaned)) == 0.0:
        raise HTTPException(status_code=400, detail="Invalid face embedding.")

    return cleaned

def normalize_email(
    email: str
):

    return email.strip().lower()


def hash_reset_token(
    token: str
):

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def send_password_reset_email(
    email: str,
    reset_url: str
):

    if not all([
        SMTP_HOST,
        SMTP_USERNAME,
        SMTP_PASSWORD,
        SMTP_FROM
    ]):

        return False

    message = EmailMessage()

    message["Subject"] = (
        "Reset your Find Your 7 password"
    )

    message["From"] = SMTP_FROM

    message["To"] = email

    message.set_content(
        f"""
Hello,

We received a request to reset your Find Your 7 Twins password.

Use this link to create a new password:

{reset_url}

This link expires in {RESET_TOKEN_MINUTES} minutes
and can only be used once.

If you did not request this, you can safely ignore this email.

Find Your 7 Twins
""".strip()
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=20
    ) as server:

        server.starttls()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.send_message(
            message
        )

    return True


# ============================================================
# REQUEST MODELS
# ============================================================

class LoginRequest(BaseModel):

    username: str

    password: str


class ForgotPasswordRequest(BaseModel):

    identifier: str


class ResetPasswordRequest(BaseModel):

    token: str

    password: str


# ============================================================
# AUTH — REGISTER
# ============================================================

@app.post("/api/auth/register")
async def register(

    username: str = Form(...),

    email: str = Form(...),

    password: str = Form(...),

    name: str = Form(...),

    country: str = Form(...),

    discoverable: bool = Form(True),

    consent: bool = Form(...),

    embedding: str = Form(...),

    photo: UploadFile = File(...)
):

    username = username.strip()

    email = normalize_email(
        email
    )

    name = name.strip()

    country = country.strip()

    # --------------------------------------------------------
    # Username
    # --------------------------------------------------------

    if len(username) < 3:

        raise HTTPException(
            status_code=400,
            detail=(
                "Username must contain "
                "at least 3 characters."
            )
        )

    if len(username) > 30:

        raise HTTPException(
            status_code=400,
            detail=(
                "Username must be "
                "30 characters or less."
            )
        )

    if not username.replace(
        "_",
        ""
    ).isalnum():

        raise HTTPException(
            status_code=400,
            detail=(
                "Username can contain "
                "letters, numbers and "
                "underscores only."
            )
        )

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    if (
        "@" not in email
        or "." not in email
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Please enter a valid "
                "email address."
            )
        )

    if len(email) > 254:

        raise HTTPException(
            status_code=400,
            detail=(
                "Email address is too long."
            )
        )

    # --------------------------------------------------------
    # Password
    # --------------------------------------------------------

    if len(password) < 8:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain "
                "at least 8 characters."
            )
        )

    if len(password.encode("utf-8")) > 72:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be "
                "72 bytes or fewer."
            )
        )

    # --------------------------------------------------------
    # Profile
    # --------------------------------------------------------

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Name is required."
        )

    if not country:

        raise HTTPException(
            status_code=400,
            detail="Country is required."
        )

    if not consent:
        raise HTTPException(
            status_code=400,
            detail="You must acknowledge the face-image processing and privacy notice."
        )

    # --------------------------------------------------------
    # Duplicate checks
    # --------------------------------------------------------

    if get_user_by_username(
        username
    ) is not None:

        raise HTTPException(
            status_code=409,
            detail=(
                "That username "
                "is already taken."
            )
        )

    if get_user_by_email(
        email
    ) is not None:

        raise HTTPException(
            status_code=409,
            detail=(
                "That email address "
                "is already registered."
            )
        )

    # --------------------------------------------------------
    # Photo
    # --------------------------------------------------------

    filename, image_path = save_upload(
        photo
    )

    embedding = parse_embedding(embedding)

    password_hash = hash_password(
        password
    )

    try:

        user_id = create_user(

            username=username,

            email=email,

            password_hash=password_hash,

            name=name,

            country=country,

            photo_path=filename,

            embedding=embedding,

            discoverable=discoverable
        )

    except Exception:

        try:

            Path(
                image_path
            ).unlink()

        except Exception:

            pass

        raise HTTPException(
            status_code=409,
            detail=(
                "Could not create account. "
                "Username or email may "
                "already exist."
            )
        )

    user = get_user(
        user_id
    )

    token = create_access_token(
        user_id
    )

    return {
        "success": True,

        "access_token": token,

        "token_type": "bearer",

        "user": public_user(
            user,
            include_email=True
        )
    }


# ============================================================
# AUTH — LOGIN
# ============================================================

@app.post("/api/auth/login")
async def login(
    request: LoginRequest
):

    username = request.username.strip()

    user = get_user_by_username(
        username
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid username "
                "or password."
            )
        )

    if not user["password_hash"]:

        raise HTTPException(
            status_code=401,
            detail=(
                "This is a legacy account. "
                "Please contact support or "
                "create a new account."
            )
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid username "
                "or password."
            )
        )

    token = create_access_token(
        user["id"]
    )

    return {
        "success": True,

        "access_token": token,

        "token_type": "bearer",

        "user": public_user(
            user,
            include_email=True
        )
    }


# ============================================================
# FORGOT PASSWORD
# ============================================================

@app.post("/api/auth/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest
):

    identifier = (
        request.identifier
        .strip()
        .lower()
    )

    generic_response = {
        "success": True,

        "message": (
            "If an account with that username "
            "or email can recover its password, "
            "a reset link has been generated."
        )
    }

    if not identifier:

        return generic_response

    user = get_user_by_username_or_email(
        identifier
    )

    if user is None:

        return generic_response

    if not user["email"]:

        return generic_response

    cleanup_expired_reset_tokens()

    raw_token = secrets.token_urlsafe(
        48
    )

    token_hash = hash_reset_token(
        raw_token
    )

    expires_at = (
        datetime.now(
            timezone.utc
        )
        +
        timedelta(
            minutes=RESET_TOKEN_MINUTES
        )
    ).isoformat()

    create_password_reset_token(
        user_id=user["id"],

        token_hash=token_hash,

        expires_at=expires_at
    )

    reset_url = (
        FRONTEND_RESET_URL
        +
        "?reset_token="
        +
        raw_token
    )

    # --------------------------------------------------------
    # Production email
    # --------------------------------------------------------

    email_sent = False

    try:

        email_sent = (
            send_password_reset_email(
                user["email"],
                reset_url
            )
        )

    except Exception as error:

        print(
            "Password reset email failed:",
            error
        )

    # Prevent unused-variable warnings.
    _ = email_sent

    # --------------------------------------------------------
    # Development mode
    # --------------------------------------------------------

    if DEV_RESET_MODE:

        print()

        print(
            "=" * 70
        )

        print(
            "PASSWORD RESET — DEVELOPMENT MODE"
        )

        print(
            f"Account: @{user['username']}"
        )

        print(
            f"Email: {user['email']}"
        )

        print(
            f"Expires: {RESET_TOKEN_MINUTES} minutes"
        )

        print(
            "Reset URL:"
        )

        print(
            reset_url
        )

        print(
            "=" * 70
        )

        print()

        return {
            **generic_response,

            "development_reset_url":
                reset_url
        }

    return generic_response


# ============================================================
# RESET PASSWORD
# ============================================================

@app.post("/api/auth/reset-password")
async def reset_password(
    request: ResetPasswordRequest
):

    token = request.token.strip()

    password = request.password

    # --------------------------------------------------------
    # Validate token
    # --------------------------------------------------------

    if not token:

        raise HTTPException(
            status_code=400,
            detail="Invalid reset link."
        )

    # --------------------------------------------------------
    # Validate password
    # --------------------------------------------------------

    if len(password) < 8:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain "
                "at least 8 characters."
            )
        )

    if len(password.encode("utf-8")) > 72:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be "
                "72 bytes or fewer."
            )
        )

    # --------------------------------------------------------
    # Hash token
    # --------------------------------------------------------

    token_hash = hash_reset_token(
        token
    )

    # --------------------------------------------------------
    # Hash new password
    # --------------------------------------------------------

    try:

        new_password_hash = hash_password(
            password
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # --------------------------------------------------------
    # ATOMIC RESET
    #
    # This performs:
    #
    #   validate token
    #       ↓
    #   update password
    #       ↓
    #   consume token
    #       ↓
    #   commit
    #
    # If anything fails:
    #
    #   rollback
    # --------------------------------------------------------

    try:

        reset_password_with_token(

            token_hash=token_hash,

            new_password_hash=new_password_hash
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except RuntimeError as error:

        print(
            "Password reset database error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The password could not be changed. "
                "Please request a new reset link."
            )
        )

    except Exception as error:

        print(
            "Unexpected password reset error:",
            error
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred "
                "while changing your password."
            )
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return {
        "success": True,

        "message": (
            "Your password has been changed "
            "successfully. You can now log in."
        )
    }


# ============================================================
# ME
# ============================================================

@app.get("/api/me")
async def me(
    current_user=Depends(
        get_current_user
    )
):

    return public_user(
        current_user,
        include_email=True
    )


# ============================================================
# PROFILE
# ============================================================

@app.put("/api/me")
async def update_profile(

    name: str = Form(...),

    country: str = Form(...),

    discoverable: bool = Form(True),

    embedding: str | None = Form(None),

    photo: UploadFile | None = File(None),

    current_user=Depends(
        get_current_user
    )
):

    name = name.strip()

    country = country.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Name is required."
        )

    if not country:

        raise HTTPException(
            status_code=400,
            detail="Country is required."
        )

    new_filename = None

    new_image_path = None

    new_embedding = None

    if (
        photo is not None
        and photo.filename
    ):

        (
            new_filename,
            new_image_path
        ) = save_upload(
            photo
        )

        if not embedding:
            try:
                Path(new_image_path).unlink()
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="A face embedding is required for a new photo.")

        new_embedding = parse_embedding(embedding)

    old_photo = current_user[
        "photo_path"
    ]

    try:

        update_user_profile(

            user_id=current_user["id"],

            name=name,

            country=country,

            discoverable=discoverable,

            photo_path=new_filename,

            embedding=new_embedding
        )

    except Exception:

        if new_image_path:

            try:

                Path(
                    new_image_path
                ).unlink()

            except Exception:

                pass

        raise HTTPException(
            status_code=500,
            detail="Could not update profile."
        )

    if (
        new_filename
        and old_photo
    ):

        old_path = (
            UPLOAD_DIR /
            old_photo
        )

        if old_path.exists():

            try:

                old_path.unlink()

            except Exception:

                pass

    updated_user = get_user(
        current_user["id"]
    )

    return {
        "success": True,

        "user": public_user(
            updated_user,
            include_email=True
        )
    }


# ============================================================
# DELETE ACCOUNT
# ============================================================

@app.delete("/api/me")
async def delete_account(
    current_user=Depends(
        get_current_user
    )
):

    photo_path = current_user[
        "photo_path"
    ]

    delete_user(
        current_user["id"]
    )

    if photo_path:

        path = (
            UPLOAD_DIR /
            photo_path
        )

        if path.exists():

            try:

                path.unlink()

            except Exception:

                pass

    return {
        "success": True,

        "message": "Account deleted."
    }


@app.get("/api/me/photo")
async def get_my_photo(current_user=Depends(get_current_user)):
    path = (UPLOAD_DIR / current_user["photo_path"]).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found.")
    from fastapi.responses import FileResponse
    return FileResponse(path)


@app.get("/api/photos/{filename}")
async def get_photo(filename: str, credentials=Depends(security)):
    safe_name = Path(filename).name
    if safe_name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=404, detail="Photo not found.")

    path = (UPLOAD_DIR / safe_name).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found.")

    # A photo is publicly retrievable only while its owning profile is discoverable.
    # The owner can still retrieve their own photo after opting out.
    from database import get_user_by_photo_path
    owner = get_user_by_photo_path(safe_name)
    if owner is None:
        raise HTTPException(status_code=404, detail="Photo not found.")

    authenticated_user = get_optional_user(credentials)
    authenticated_user_id = authenticated_user["id"] if authenticated_user else None

    if not owner["discoverable"] and authenticated_user_id != owner["id"]:
        raise HTTPException(status_code=404, detail="Photo not found.")

    from fastapi.responses import FileResponse
    return FileResponse(path)


# ============================================================
# PUBLIC USERS
# ============================================================

@app.get("/api/users/{user_id}")
async def get_public_user(
    user_id: int,
    current_user=Depends(get_current_user)
):

    user = get_user(
        user_id
    )

    if user is None or (not user["discoverable"] and user["id"] != current_user["id"]):
        raise HTTPException(status_code=404, detail="User not found.")

    return public_user(user)


@app.get("/api/users")
async def users(current_user=Depends(get_current_user)):
    return [
        public_user(row)
        for row in get_all_users()
        if row["discoverable"] or row["id"] == current_user["id"]
    ]


# ============================================================
# TWINS
# ============================================================

@app.get("/api/twins/me")
async def find_my_twins(
    current_user=Depends(
        get_current_user
    )
):

    my_embedding = embedding_from_row(
        current_user
    )

    candidates = (
        get_discoverable_users(
            current_user["id"]
        )
    )

    matches = []

    for candidate in candidates:

        candidate_embedding = (
            embedding_from_row(
                candidate
            )
        )

        similarity = cosine_similarity(
            my_embedding,
            candidate_embedding
        )

        matches.append({

            "user":
                public_user(candidate),

            "similarity":
                similarity,

            "similarity_percent":
                round(
                    similarity * 100,
                    2
                )
        })

    matches.sort(
        key=lambda x:
            x["similarity"],
        reverse=True
    )

    top_seven = matches[:7]

    return {

        "count":
            len(top_seven),

        "twins":
            top_seven
    }


@app.get("/api/twins/{user_id}")
async def find_twins_legacy(

    user_id: int,

    current_user=Depends(
        get_current_user
    )
):

    if user_id != current_user["id"]:

        raise HTTPException(
            status_code=403,
            detail=(
                "You can only access "
                "your own twin results."
            )
        )

    return await find_my_twins(
        current_user
    )


# ============================================================
# SWIPES
# ============================================================

@app.post("/api/swipes")
async def swipe(

    target_user_id: int = Form(...),

    direction: str = Form(...),

    current_user=Depends(
        get_current_user
    )
):

    direction = (
        direction
        .lower()
        .strip()
    )

    if direction not in {
        "like",
        "pass"
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Direction must be "
                "'like' or 'pass'."
            )
        )

    user_id = current_user[
        "id"
    ]

    if target_user_id == user_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot swipe "
                "on yourself."
            )
        )

    target = get_user(
        target_user_id
    )

    if target is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Target user "
                "was not found."
            )
        )

    if not target["discoverable"]:

        raise HTTPException(
            status_code=400,
            detail=(
                "That user is not "
                "currently discoverable."
            )
        )

    # --------------------------------------------------------
    # Permanent atomic swipe
    # --------------------------------------------------------

    created = create_swipe_once(

        user_id=user_id,

        target_user_id=target_user_id,

        direction=direction
    )

    if not created:

        raise HTTPException(
            status_code=409,
            detail=(
                "You have already made "
                "a Twin decision for this person."
            )
        )

    mutual_match = False

    if direction == "like":

        mutual_match = (
            is_mutual_match(
                user_id,
                target_user_id
            )
        )

    return {

        "success": True,

        "direction":
            direction,

        "match":
            mutual_match,

        "target":
            public_user(target),

        "message": (
            "It's a Twin Match!"
            if mutual_match
            else "Twin decision saved."
        )
    }


# ============================================================
# SWIPE HISTORY
# ============================================================

@app.get("/api/swipes/me")
async def my_swipes(
    current_user=Depends(
        get_current_user
    )
):

    rows = get_user_swipes(
        current_user["id"]
    )

    return {

        "swipes": [

            {
                "target_user_id":
                    row["target_user_id"],

                "direction":
                    row["direction"],

                "created_at":
                    row["created_at"]
            }

            for row in rows
        ]
    }


# ============================================================
# MATCHES
# ============================================================

@app.get("/api/matches/me")
async def my_matches(
    current_user=Depends(
        get_current_user
    )
):

    rows = get_matches(
        current_user["id"]
    )

    return {

        "count":
            len(rows),

        "matches":
            [
                public_user(row)
                for row in rows
            ]
    }


@app.get("/health")
async def health():
    try:
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return {"status": "ok", "database": "ok", "version": "3.1.0"}


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
async def root():

    return {

        "app":
            "Find Your 7 Twins",

        "status":
            "online",

        "version":
            "3.1.0",

        "features": [

            "visual twin discovery",

            "permanent discovery decisions",

            "automatic twin replenishment",

            "mutual twin matching",

            "secure password recovery"

        ]
    }