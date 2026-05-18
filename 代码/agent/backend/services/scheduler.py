from datetime import datetime, timedelta
from typing import List
from backend.models.schemas import Course, Task


class Scheduler:
    def now(self):
        return datetime.now()

    def parse_time(self, time_str):
        """解析 HH:MM 为今天的 datetime"""
        h, m = map(int, time_str.split(":"))
        now = self.now()
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    def parse_datetime(self, dt_str):
        """解析 ISO 格式字符串"""
        return datetime.fromisoformat(dt_str)

    def get_today_courses(self, courses: List[Course]):
        today = self.now().isoweekday()  # 1=Monday
        return [c for c in courses if c.day_of_week == today]

    def get_tomorrow_courses(self, courses: List[Course]):
        tomorrow = (self.now() + timedelta(days=1)).isoweekday()
        return [c for c in courses if c.day_of_week == tomorrow]

    def generate_plan(self, courses: List[Course], tasks: List[Task], days=3):
        """
        粗颗粒度规划：将任务插入课表空闲时间。
        返回每天的时间段列表。
        """
        now = self.now()
        plan = []

        for i in range(days):
            day_date = now + timedelta(days=i)
            day_of_week = day_date.isoweekday()
            # 该天课程（含固定活动）
            day_courses = sorted(
                [c for c in courses if c.day_of_week == day_of_week],
                key=lambda x: self.parse_time(x.start_time)
            )

            # 空闲区间
            free_intervals = []
            start = datetime(day_date.year, day_date.month, day_date.day, 8, 0)  # 8:00起
            for course in day_courses:
                course_start = self.parse_time(course.start_time)
                course_end = self.parse_time(course.end_time)
                if start < course_start:
                    free_intervals.append((start, course_start))
                start = max(start, course_end)
            # 晚上到23:00
            end_of_day = datetime(day_date.year, day_date.month, day_date.day, 23, 0)
            if start < end_of_day:
                free_intervals.append((start, end_of_day))

            # 分配任务
            tasks_sorted = sorted(tasks, key=lambda t: self.parse_datetime(t.deadline))
            day_schedule = []
            # 先添加课程
            for c in day_courses:
                day_schedule.append({
                    "type": "course",
                    "time": f"{c.start_time}-{c.end_time}",
                    "title": c.name,
                    "location": c.location
                })

            for task in tasks_sorted:
                if task.completed:
                    continue
                # 寻找足够长的空闲
                for idx, (s, e) in enumerate(free_intervals):
                    duration = (e - s).total_seconds() / 3600
                    if duration >= task.estimated_hours:
                        # 安排在此
                        task_start = s
                        task_end = s + timedelta(hours=task.estimated_hours)
                        day_schedule.append({
                            "type": "task",
                            "time": f"{task_start.strftime('%H:%M')}-{task_end.strftime('%H:%M')}",
                            "title": task.title,
                            "deadline": task.deadline
                        })
                        # 更新空闲区间
                        if task_end < e:
                            free_intervals[idx] = (task_end, e)
                        else:
                            free_intervals.pop(idx)
                        break
                else:
                    # 无足够空闲，标记为未安排
                    day_schedule.append({
                        "type": "unscheduled",
                        "title": task.title,
                        "reason": "当日无足够空闲"
                    })

            plan.append({
                "date": day_date.strftime("%Y-%m-%d"),
                "day_of_week": day_of_week,
                "schedule": sorted(day_schedule, key=lambda x: x["time"] if "time" in x else "23:59")
            })

        return plan