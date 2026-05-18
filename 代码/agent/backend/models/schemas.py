from pydantic import BaseModel
from typing import List, Optional

class UserLogin(BaseModel):
    username: str
    password: str

class Course(BaseModel):
    id: Optional[str] = None
    name: str
    teacher: Optional[str] = ""
    location: Optional[str] = ""
    weeks: List[int] = []
    day_of_week: int
    start_time: str
    end_time: str
    items: List[str] = []

class Task(BaseModel):
    id: Optional[str] = None
    title: str
    course: Optional[str] = None
    deadline: str
    estimated_hours: float = 1.0
    completed: bool = False

class PlanRequest(BaseModel):
    days: Optional[int] = 3

class PlanResponse(BaseModel):
    plan: List[dict]

class ReminderResponse(BaseModel):
    reminders: List[dict]