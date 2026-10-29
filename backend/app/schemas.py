from datetime import datetime, date, time
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

class Register(Strict):
    username: str = Field(pattern=r'^[a-zA-Z0-9_]{3,40}$')
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    @field_validator('username', 'email')
    @classmethod
    def lower(cls, value): return value.lower()

class Login(Strict):
    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class Verify(Strict):
    challenge_id: str
    code: str = Field(pattern=r'^\d{6}$')

class Resend(Strict):
    challenge_id: str

class EmployeeEdit(Strict):
    full_name: str = Field(min_length=2, max_length=100)
    department: str = Field(default='', max_length=100)
    phone: str = Field(default='', max_length=20)
    role: Literal['admin', 'employee'] = 'employee'
    active: bool = True

class ProfileEdit(Strict):
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(default='', max_length=20)

class SiteData(Strict):
    name: str = Field(min_length=2, max_length=100)
    address: str = Field(default='', max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_m: int = Field(ge=20, le=2000, default=150)

class ShiftData(Strict):
    name: str = Field(min_length=2, max_length=100)
    site_id: str
    start_time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    end_time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    grace_minutes: int = Field(default=10, ge=0, le=120)
    @model_validator(mode='after')
    def duration(self):
        if self.start_time == self.end_time: raise ValueError('Giờ vào và giờ ra phải khác nhau.')
        return self

class AssignmentData(Strict):
    user_id: str
    shift_id: str
    work_date: date

class Evidence(Strict):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(gt=0, le=10000)
    is_mocked: bool = False
    captured_at: datetime
    motion_rms: float = Field(ge=0, le=200)
    motion_samples: int = Field(ge=15, le=2000)
    motion_duration_ms: int = Field(ge=2000, le=15000)
    qr_token: str = Field(min_length=20, max_length=2000)
    @field_validator('captured_at')
    @classmethod
    def tz(cls, value):
        if value.tzinfo is None: raise ValueError('Thời gian phải có múi giờ.')
        return value

class CheckData(Evidence):
    assignment_id: str
    action: Literal['in', 'out']

class CorrectionData(Strict):
    assignment_id: str
    requested_in: datetime
    requested_out: datetime | None = None
    reason: str = Field(min_length=10, max_length=1000)
    evidence: Evidence | None = None
    @model_validator(mode='after')
    def times(self):
        for value in (self.requested_in, self.requested_out):
            if value is not None and value.tzinfo is None: raise ValueError('Thời gian phải có múi giờ.')
        if self.requested_out and self.requested_out <= self.requested_in:
            raise ValueError('Giờ ra phải sau giờ vào.')
        return self

class Review(Strict):
    decision: Literal['approved', 'rejected']
    note: str = Field(min_length=3, max_length=1000)
