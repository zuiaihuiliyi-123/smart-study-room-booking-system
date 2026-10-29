from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    open_time: str = "08:00"
    close_time: str = "22:00"
    capacity: int = 0


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
