import os
import secrets
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Security,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy import create_engine


# Set STUDENT_API_KEY in your environment before running in a real deployment.
# This fallback is only for local development and testing.
API_KEY = os.getenv("STUDENT_API_KEY", "dev-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./students.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    course: Mapped[str] = mapped_column(String(100), nullable=False)


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentCreate(InputModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(strict=True, ge=16, le=100)
    course: str = Field(min_length=2, max_length=100)


class StudentUpdate(InputModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    age: int | None = Field(default=None, strict=True, ge=16, le=100)
    course: str | None = Field(default=None, min_length=2, max_length=100)

    @model_validator(mode="after")
    def at_least_one_field_must_be_supplied(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    age: int
    course: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="APIKeyAuth",
    description="Enter the API key configured in STUDENT_API_KEY.",
    auto_error=False,
)


def require_api_key(api_key: Annotated[str | None, Security(api_key_header)]):
    if not api_key or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing or invalid",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def error_response(code: str, message: str, details: Any = None):
    return {"error": {"code": code, "message": message, "details": details}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Student Management API",
    description=(
        "Student CRUD API with API-key authentication. "
        "All /students routes require the X-API-Key header."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    code_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
    }
    code = code_by_status.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code, message, details),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "message": item["msg"],
            "type": item["type"],
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            "VALIDATION_ERROR",
            "Request data is invalid",
            details,
        ),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request, exc: Exception):
    # Do not expose stack traces or internal exception details to API clients.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected server error occurred",
            None,
        ),
    )


@app.get("/")
def home():
    return {"message": "Student Management API is running", "docs": "/docs"}


router = APIRouter(
    prefix="/students",
    tags=["Students (API key required)"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Annotated[Session, Depends(get_db)]):
    existing = db.scalar(select(Student).where(Student.email == str(payload.email)))
    if existing:
        raise HTTPException(status_code=409, detail="A student with this email already exists")

    student = Student(**payload.model_dump())
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A student with this email already exists")
    db.refresh(student)
    return student


@router.get("/", response_model=list[StudentResponse])
def get_students(db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(Student).order_by(Student.id)).all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Annotated[Session, Depends(get_db)]):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"] is not None:
        updates["email"] = str(updates["email"])
        duplicate = db.scalar(
            select(Student).where(
                Student.email == updates["email"],
                Student.id != student_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Another student already uses this email")

    for field, value in updates.items():
        if value is not None:
            setattr(student, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another student already uses this email")
    db.refresh(student)
    return student


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Annotated[Session, Depends(get_db)]):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
    return {"message": f"Student {student_id} deleted successfully"}


app.include_router(router)
