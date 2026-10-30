from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid4())

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100), default='')
    phone: Mapped[str] = mapped_column(String(20), default='')
    role: Mapped[str] = mapped_column(String(20), default='employee')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Challenge(Base):
    __tablename__ = 'challenges'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    purpose: Mapped[str] = mapped_column(String(20))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    resends: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


# These tables are additive: existing accounts, sessions and attendance rows do
# not need an ALTER TABLE or destructive reset when the application is updated.
class BiometricDevice(Base):
    __tablename__ = 'biometric_devices'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    device_name: Mapped[str] = mapped_column(String(100))
    public_key: Mapped[str] = mapped_column(Text)
    key_fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    face_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class BiometricChallenge(Base):
    __tablename__ = 'biometric_challenges'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    # Enrollment allocates this identifier before the credential exists.
    device_id: Mapped[str] = mapped_column(String(36), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
    payload: Mapped[str] = mapped_column(String(512))
    pending_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_name: Mapped[str] = mapped_column(String(100), default='')
    steps: Mapped[list] = mapped_column(JSON, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class BiometricSessionLink(Base):
    __tablename__ = 'biometric_session_links'
    session_id: Mapped[str] = mapped_column(ForeignKey('auth_sessions.id'), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey('biometric_devices.id'), index=True)

class Throttle(Base):
    __tablename__ = 'throttles'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

class Site(Base):
    __tablename__ = 'sites'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255), default='')
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[int] = mapped_column(Integer, default=150)
    qr_version: Mapped[int] = mapped_column(Integer, default=1)

class Shift(Base):
    __tablename__ = 'shifts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    site_id: Mapped[str] = mapped_column(ForeignKey('sites.id'))
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    grace_minutes: Mapped[int] = mapped_column(Integer, default=10)

class Assignment(Base):
    __tablename__ = 'assignments'
    __table_args__ = (UniqueConstraint('user_id', 'shift_id', 'work_date'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    shift_id: Mapped[str] = mapped_column(ForeignKey('shifts.id'))
    work_date: Mapped[str] = mapped_column(String(10))

class Attendance(Base):
    __tablename__ = 'attendances'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assignment_id: Mapped[str] = mapped_column(ForeignKey('assignments.id'), unique=True)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='present')
    in_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    out_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class Correction(Base):
    __tablename__ = 'corrections'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assignment_id: Mapped[str] = mapped_column(ForeignKey('assignments.id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    requested_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requested_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(1000))
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    review_note: Mapped[str] = mapped_column(String(1000), default='')
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

engine = create_engine(DATABASE_URL, pool_pre_ping=True,
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db

def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def public(obj):
    hidden = {'password_hash', 'code_hash', 'qr_version', 'public_key',
              'key_fingerprint', 'face_template', 'payload', 'pending_key'}
    return {column.name: (aware(value).isoformat() if isinstance(value, datetime) else value)
            for column in obj.__table__.columns
            if column.name not in hidden
            for value in [getattr(obj, column.name)]}
