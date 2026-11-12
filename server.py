import io
import json
import logging
import os
import re
import secrets
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from threading import Lock
from typing import Literal

import psycopg
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi import Path as PathParam, Request, Response
from fastapi.responses import FileResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from starlette.middleware.sessions import SessionMiddleware


logger = logging.getLogger(__name__)
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
ADMIN_PAGE = os.path.join(os.path.dirname(__file__), "admin.html")
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60
login_attempts = defaultdict(list)
login_attempts_lock = Lock()


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    entryType: Literal["1", "2", "3"]
    teamName: str = Field(default="", max_length=120)
    member1Name: str = Field(min_length=1, max_length=120)
    member1StudentId: str = Field(min_length=1, max_length=40)
    member1Class: str = Field(min_length=1, max_length=120)
    contactEmail: str = Field(min_length=3, max_length=254)
    contactPhone: str = Field(min_length=6, max_length=30)
    member2Name: str = Field(default="", max_length=120)
    member2StudentId: str = Field(default="", max_length=40)
    member2Class: str = Field(default="", max_length=120)
    member3Name: str = Field(default="", max_length=120)
    member3StudentId: str = Field(default="", max_length=40)
    member3Class: str = Field(default="", max_length=120)
    productName: str = Field(min_length=1, max_length=200)
    productTopic: Literal["learning", "community"]
    productFormat: Literal[
        "Ứng dụng máy tính / điện thoại",
        "Website",
        "Chatbot",
        "Công cụ phân tích dữ liệu",
        "Quy trình tích hợp AI",
        "Prototype có thể vận hành",
        "Hình thức khác",
    ]

    @model_validator(mode="after")
    def validate_team(self):
        member_count = int(self.entryType)
        if member_count > 1 and not self.teamName:
            raise ValueError("Vui lòng nhập tên đội.")

        for number in range(2, 4):
            member_fields = (
                getattr(self, f"member{number}Name"),
                getattr(self, f"member{number}StudentId"),
                getattr(self, f"member{number}Class"),
            )
            has_member_data = any(member_fields)
            if number <= member_count and not all(member_fields):
                raise ValueError(f"Vui lòng điền đủ thông tin thành viên {number}.")
            if number > member_count and has_member_data:
                raise ValueError(f"Thông tin thành viên {number} không phù hợp với số lượng đội.")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.contactEmail):
            raise ValueError("Email liên hệ không hợp lệ.")
        return self


def connect_database():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL chưa được cấu hình. Hãy thêm connection string Neon vào file .env."
        )
    return psycopg.connect(
        DATABASE_URL,
        connect_timeout=10,
        row_factory=dict_row,
    )


def initialize_database():
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL,
                entry_type SMALLINT NOT NULL CHECK (entry_type BETWEEN 1 AND 3),
                team_name TEXT NOT NULL,
                members_json JSONB NOT NULL,
                contact_email TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                product_name TEXT NOT NULL,
                product_topic TEXT NOT NULL,
                product_format TEXT NOT NULL,
                soft_copy_submitted BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        connection.execute(
            """
            ALTER TABLE registrations
            ADD COLUMN IF NOT EXISTS soft_copy_submitted
            BOOLEAN NOT NULL DEFAULT FALSE
            """
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="AI Innovation Challenge Registration API", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="strict",
    https_only=os.environ.get("SESSION_HTTPS_ONLY", "").lower() in {"1", "true", "yes"},
    max_age=8 * 60 * 60,
)


@app.middleware("http")
async def disable_admin_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/admin" or request.url.path.startswith("/api/admin/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/register", status_code=201)
def create_registration(registration: Registration):
    members = [
        {
            "name": getattr(registration, f"member{number}Name"),
            "student_id": getattr(registration, f"member{number}StudentId"),
            "class_name": getattr(registration, f"member{number}Class"),
        }
        for number in range(1, int(registration.entryType) + 1)
    ]

    try:
        with connect_database() as connection:
            cursor = connection.execute(
                """
                INSERT INTO registrations (
                    created_at, entry_type, team_name, members_json,
                    contact_email, contact_phone, product_name,
                    product_topic, product_format
                ) VALUES (now(), %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    int(registration.entryType),
                    registration.teamName,
                    Jsonb(members),
                    registration.contactEmail,
                    registration.contactPhone,
                    registration.productName,
                    registration.productTopic,
                    registration.productFormat,
                ),
            )
            registration_id = cursor.fetchone()["id"]
    except psycopg.Error as error:
        logger.exception("Could not save registration")
        raise HTTPException(
            status_code=503,
            detail="Máy chủ chưa thể kết nối hoặc lưu dữ liệu vào database. Vui lòng thử lại sau.",
        ) from error

    return {"id": registration_id, "message": "Đăng ký đã được lưu thành công."}


class AdminLogin(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class SubmissionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submitted: StrictBool


def require_admin(request: Request) -> str:
    if not ADMIN_USERNAME or request.session.get("admin_username") != ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    return request.session["csrf_token"]


def require_csrf(request: Request, csrf_token: str):
    expected_token = require_admin(request)
    if not secrets.compare_digest(csrf_token, expected_token):
        raise HTTPException(status_code=403, detail="Phiên làm việc không hợp lệ. Hãy tải lại trang.")


def enforce_login_limit(client_ip: str):
    now = time.monotonic()
    with login_attempts_lock:
        attempts = [
            timestamp
            for timestamp in login_attempts[client_ip]
            if now - timestamp < LOGIN_LOCKOUT_SECONDS
        ]
        login_attempts[client_ip] = attempts
        if len(attempts) >= LOGIN_FAILURE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 15 phút.",
                headers={"Retry-After": str(LOGIN_LOCKOUT_SECONDS)},
            )


def record_login_failure(client_ip: str):
    with login_attempts_lock:
        login_attempts[client_ip].append(time.monotonic())


def clear_login_failures(client_ip: str):
    with login_attempts_lock:
        login_attempts.pop(client_ip, None)


def require_csrf_header(request: Request):
    require_csrf(request, request.headers.get("X-CSRF-Token", ""))


@app.get("/admin", response_class=FileResponse)
def admin_page():
    return FileResponse(ADMIN_PAGE, headers={"Cache-Control": "no-store"})


@app.get("/admin.js")
def admin_script():
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin.js"))


@app.get("/admin.css")
def admin_stylesheet():
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin.css"))


@app.post("/api/admin/login")
def admin_login(credentials: AdminLogin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    enforce_login_limit(client_ip)
    username_matches = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    password_matches = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not ADMIN_USERNAME or not ADMIN_PASSWORD or not username_matches or not password_matches:
        record_login_failure(client_ip)
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng.")

    clear_login_failures(client_ip)
    request.session.clear()
    request.session["admin_username"] = ADMIN_USERNAME
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    return {"username": ADMIN_USERNAME, "csrf_token": request.session["csrf_token"]}


@app.post("/api/admin/logout", status_code=204)
def admin_logout(request: Request):
    require_csrf_header(request)
    request.session.clear()
    return Response(status_code=204)


@app.get("/api/admin/registrations")
def list_registrations(request: Request):
    require_admin(request)
    try:
        with connect_database() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, entry_type, team_name, members_json,
                       contact_email, contact_phone, product_name, product_topic,
                       product_format, soft_copy_submitted
                FROM registrations
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    except psycopg.Error as error:
        logger.exception("Could not retrieve registrations for admin")
        raise HTTPException(
            status_code=503, detail="Không thể tải danh sách đăng ký."
        ) from error

    return [
        {**row, "created_at": row["created_at"].isoformat()}
        for row in rows
    ]


@app.patch("/api/admin/registrations/{registration_id}/soft-copy")
def update_soft_copy_status(
    request: Request,
    registration_id: int = PathParam(gt=0),
    status: SubmissionStatus = Body(...),
):
    require_csrf_header(request)
    try:
        with connect_database() as connection:
            cursor = connection.execute(
                """
                UPDATE registrations
                SET soft_copy_submitted = %s
                WHERE id = %s
                RETURNING id, soft_copy_submitted
                """,
                (status.submitted, registration_id),
            )
            row = cursor.fetchone()
    except psycopg.Error as error:
        logger.exception("Could not update soft-copy status")
        raise HTTPException(
            status_code=503, detail="Không thể cập nhật trạng thái hồ sơ."
        ) from error

    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đăng ký.")
    return row


def safe_excel_text(value):
    if isinstance(value, str) and re.match(r"^\s*[=+\-@\t\r]", value):
        return f"'{value}"
    return value


@app.get("/api/admin/registrations/export.xlsx")
def export_registrations(request: Request):
    require_admin(request)
    try:
        with connect_database() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, entry_type, team_name, members_json,
                       contact_email, contact_phone, product_name, product_topic,
                       product_format, soft_copy_submitted
                FROM registrations
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    except psycopg.Error as error:
        logger.exception("Could not export registrations")
        raise HTTPException(
            status_code=503, detail="Không thể xuất danh sách đăng ký."
        ) from error

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Danh sach dang ky"
    worksheet.append(
        [
            "Mã đăng ký",
            "Thời gian đăng ký",
            "Hình thức",
            "Tên đội",
            "Thành viên 1",
            "MSSV 1",
            "Lớp/ngành 1",
            "Thành viên 2",
            "MSSV 2",
            "Lớp/ngành 2",
            "Thành viên 3",
            "MSSV 3",
            "Lớp/ngành 3",
            "Email liên hệ",
            "Số điện thoại",
            "Tên sản phẩm",
            "Chủ đề",
            "Hình thức sản phẩm",
            "Đã nộp hồ sơ bản mềm",
        ]
    )
    for cell in worksheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(fill_type="solid", fgColor="344CB1")
    worksheet.freeze_panes = "A2"

    topic_labels = {
        "learning": "Ứng dụng AI trong học tập",
        "community": "Ứng dụng AI phục vụ cộng đồng",
    }
    for row in rows:
        members = row["members_json"]
        member_columns = []
        for index in range(3):
            member = members[index] if index < len(members) else {}
            member_columns.extend(
                safe_excel_text(member.get(field, ""))
                for field in ("name", "student_id", "class_name")
            )

        worksheet.append(
            [
                row["id"],
                row["created_at"].isoformat(),
                f'{row["entry_type"]} thành viên',
                safe_excel_text(row["team_name"]),
                *member_columns,
                safe_excel_text(row["contact_email"]),
                safe_excel_text(row["contact_phone"]),
                safe_excel_text(row["product_name"]),
                topic_labels.get(row["product_topic"], row["product_topic"]),
                safe_excel_text(row["product_format"]),
                "Đã nộp" if row["soft_copy_submitted"] else "Chưa nộp",
            ]
        )

    worksheet.auto_filter.ref = worksheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="danh-sach-doi-thi.xlsx"'},
    )
