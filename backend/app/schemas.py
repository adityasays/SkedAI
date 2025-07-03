from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class BookingRequest(BaseModel):
    message: str

class AvailabilityRequest(BaseModel):
    message: str

class BookingResponse(BaseModel):
    message: str
    success: bool
    event_id: Optional[str] = None
    event_time: Optional[str] = None

class CalendarStatsResponse(BaseModel):
    total_events_this_week: int
    cache_hit_ratio: float
    api_health: str
    last_update: str
    error: Optional[str] = None