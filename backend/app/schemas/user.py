import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    person_id: Optional[uuid.UUID]
    must_change_password: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}
