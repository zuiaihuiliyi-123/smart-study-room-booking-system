from fastapi import APIRouter

from app.api.v1 import (
    attendance,
    auth,
    blacklist,
    complaints,
    dashboard,
    messages,
    reservations,
    reviews,
    rooms,
    seats,
    users,
    violations,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(rooms.router)
api_router.include_router(seats.router)
api_router.include_router(reservations.router)
api_router.include_router(attendance.router)
api_router.include_router(violations.router)
api_router.include_router(reviews.router)
api_router.include_router(complaints.router)
api_router.include_router(blacklist.router)
api_router.include_router(dashboard.router)
api_router.include_router(messages.router)
