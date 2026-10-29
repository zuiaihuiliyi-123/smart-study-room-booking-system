from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    open_time: str = Field(
        default="08:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    close_time: str = Field(
        default="22:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$"
    )
    capacity: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_time_range(self) -> "RoomCreate":
        if self.open_time >= self.close_time:
            raise ValueError("开放时间必须早于关闭时间")
        return self


class RoomRead(ORMModel):
    id: int
    name: str
    location: str
    open_time: str
    close_time: str
    capacity: int
    enabled: bool


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class AreaRead(ORMModel):
    id: int
    room_id: int
    name: str
