from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from backend.models.schemas import (
    UserLogin, Course, Task, PlanRequest, PlanResponse,
    ReminderResponse
)
from backend.services.storage import Storage
from backend.services.vision import analyze_image, check_connection, is_healthy, chat_with_model
from backend.services.scheduler import Scheduler
import uuid

router = APIRouter()
storage = Storage()
scheduler = Scheduler()


# ---------- 健康检查 ----------
@router.get("/health")
async def health_check():
    """
    健康检查端点，检查模型服务连接状态
    """
    model_status = "healthy" if is_healthy() else "unhealthy"
    
    return {
        "status": "ok",
        "service": "campus-assistant",
        "model": {
            "status": model_status,
            "connected": is_healthy()
        }
    }


@router.post("/health/check")
async def trigger_health_check():
    """
    主动触发模型连接检查
    """
    success = check_connection()
    
    return {
        "status": "ok" if success else "error",
        "message": "模型连接成功" if success else "模型连接失败，请检查API Key和网络连接",
        "connected": success
    }


# ---------- 认证模拟 ----------
@router.post("/login")
async def login(user: UserLogin):
    # 模拟登录，简单生成token
    token = str(uuid.uuid4())
    storage.save_user_token(user.username, token)
    return {"token": token, "username": user.username}


# ---------- 课表管理 ----------
@router.post("/courses/import")
async def import_course_from_image(
        token: str = Form(...),
        image: UploadFile = File(...)
):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    # 调用视觉模型识别课表
    content = await image.read()
    result = await analyze_image(content, "course_table")
    # result 期望结构: {"courses": [{...}]}
    courses = result.get("courses", [])

    saved_courses = []
    for c in courses:
        course = Course(
            name=c.get("name"),
            teacher=c.get("teacher", ""),
            location=c.get("location", ""),
            weeks=c.get("weeks", []),
            day_of_week=c.get("day_of_week"),
            start_time=c.get("start_time"),
            end_time=c.get("end_time"),
            items=c.get("items", [])  # 物品清单，识别时可尝试提取，否则默认
        )
        saved_courses.append(storage.add_course(user["username"], course))

    return {"message": "课表导入成功", "courses": saved_courses}


@router.get("/courses/today")
async def get_today_courses(token: str):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)
    today_courses = scheduler.get_today_courses(storage.get_courses(user["username"]))
    return {"courses": today_courses}


@router.get("/courses/tomorrow")
async def get_tomorrow_courses(token: str):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)
    return {"courses": scheduler.get_tomorrow_courses(storage.get_courses(user["username"]))}


# ---------- 任务管理 ----------
@router.post("/tasks/add")
async def add_task_manual(
        token: str = Form(...),
        title: str = Form(...),
        course: str = Form(None),
        deadline: str = Form(...),  # ISO格式
        estimated_hours: float = Form(1.0)
):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)
    task = Task(
        title=title,
        course=course,
        deadline=deadline,
        estimated_hours=estimated_hours,
        completed=False
    )
    saved = storage.add_task(user["username"], task)
    return {"message": "任务添加成功", "task": saved}


@router.post("/tasks/import")
async def import_task_from_image(
        token: str = Form(...),
        image: UploadFile = File(...)
):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)

    content = await image.read()
    result = await analyze_image(content, "task")
    tasks_data = result.get("tasks", [])
    saved_tasks = []
    for t in tasks_data:
        task = Task(
            title=t.get("title"),
            course=t.get("course"),
            deadline=t.get("deadline"),
            estimated_hours=t.get("estimated_hours", 1.0),
            completed=False
        )
        saved_tasks.append(storage.add_task(user["username"], task))
    return {"message": "识别并添加任务成功", "tasks": saved_tasks}


@router.put("/tasks/complete")
async def complete_task(token: str, task_id: str):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)
    storage.complete_task(user["username"], task_id)
    return {"message": "任务已完成"}


@router.get("/tasks/uncompleted")
async def get_uncompleted_tasks(token: str):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)
    return {"tasks": storage.get_uncompleted_tasks(user["username"])}


# ---------- 智能规划 ----------
@router.post("/plan")
async def generate_plan(token: str, request: PlanRequest):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)

    courses = storage.get_courses(user["username"])
    tasks = storage.get_uncompleted_tasks(user["username"])
    plan = scheduler.generate_plan(courses, tasks, request.days or 3)
    return {"plan": plan}


# ---------- 提醒接口（前端轮询） ----------
@router.get("/reminders")
async def get_reminders(token: str):
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401)

    now = scheduler.now()
    reminders = []

    # 上课提醒：课前30分钟
    today_courses = scheduler.get_today_courses(storage.get_courses(user["username"]))
    for c in today_courses:
        course_start = scheduler.parse_time(c.start_time)
        delta = (course_start - now).total_seconds() / 60
        if 0 <= delta <= 30 and not storage.is_reminded(user["username"], f"course_{c.id}_{now.strftime('%Y%m%d')}"):
            reminders.append({
                "type": "course",
                "course_name": c.name,
                "location": c.location,
                "items": c.items,
                "time": c.start_time,
                "delta_minutes": int(delta),
                "id": c.id
            })
            storage.mark_reminded(user["username"], f"course_{c.id}_{now.strftime('%Y%m%d')}")

    # 任务截止提醒：1天/1小时
    for t in storage.get_uncompleted_tasks(user["username"]):
        dl = scheduler.parse_datetime(t.deadline)
        diff_hours = (dl - now).total_seconds() / 3600
        reminder_key = f"task_{t.id}_{dl.strftime('%Y%m%d%H')}"
        if 0.5 <= diff_hours <= 1.5 and not storage.is_reminded(user["username"], reminder_key):
            reminders.append({
                "type": "task_deadline",
                "title": t.title,
                "deadline": t.deadline,
                "urgency": "1小时",
                "task_id": t.id
            })
            storage.mark_reminded(user["username"], reminder_key)
        elif 23.5 <= diff_hours <= 24.5 and not storage.is_reminded(user["username"], reminder_key):
            reminders.append({
                "type": "task_deadline",
                "title": t.title,
                "deadline": t.deadline,
                "urgency": "明天",
                "task_id": t.id
            })
            storage.mark_reminded(user["username"], reminder_key)

    # 明天课程汇总（每天20:00-21:00间仅提醒一次）
    if now.hour == 21 and not storage.is_reminded(user["username"], f"tomorrow_{now.strftime('%Y%m%d')}"):
        tomorrow = scheduler.get_tomorrow_courses(storage.get_courses(user["username"]))
        if tomorrow:
            reminders.append({
                "type": "tomorrow_summary",
                "courses": [c.name for c in tomorrow],
                "summary": "、".join([f"{c.name} {c.start_time}-{c.end_time}" for c in tomorrow])
            })
        storage.mark_reminded(user["username"], f"tomorrow_{now.strftime('%Y%m%d')}")

    return {"reminders": reminders}


@router.post("/reminders/snooze_task")
async def snooze_task(token: str, task_id: str):
    # 稍后提醒：将任务提醒标记重置，相当于一小时后再次提醒（通过前端存储）
    # 这里简化处理：后端不做特殊标记，前端控制一小时内不再请求同任务提醒
    return {"message": "已延迟提醒"}


# ---------- AI聊天接口 ----------
@router.post("/chat")
async def chat(request: Request):
    """
    AI聊天接口，支持JSON和表单数据
    """
    try:
        # 尝试解析JSON
        data = await request.json()
        token = data.get("token")
        prompt = data.get("prompt")
    except:
        # 如果JSON解析失败，尝试表单数据
        form_data = await request.form()
        token = form_data.get("token")
        prompt = form_data.get("prompt")
    
    user = storage.get_user_by_token(token)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "请输入消息内容"})
    
    response = await chat_with_model(prompt)
    return {"response": response}