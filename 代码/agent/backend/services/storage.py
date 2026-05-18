from datetime import datetime
import uuid

class Storage:
    def __init__(self):
        self.users = {}  # token -> username
        self.courses = {}  # username -> [course]
        self.tasks = {}  # username -> [task]
        self.reminders = {}  # username -> set(reminder_key)

    def save_user_token(self, username, token):
        self.users[token] = username

    def get_user_by_token(self, token):
        username = self.users.get(token)
        if not username:
            return None
        return {"username": username, "token": token}

    def add_course(self, username, course):
        course.id = str(uuid.uuid4())
        if username not in self.courses:
            self.courses[username] = []
        self.courses[username].append(course)
        return course

    def get_courses(self, username):
        return self.courses.get(username, [])

    def add_task(self, username, task):
        task.id = str(uuid.uuid4())
        task.completed = False
        if username not in self.tasks:
            self.tasks[username] = []
        self.tasks[username].append(task)
        return task

    def get_uncompleted_tasks(self, username):
        return [t for t in self.tasks.get(username, []) if not t.completed]

    def complete_task(self, username, task_id):
        for t in self.tasks.get(username, []):
            if t.id == task_id:
                t.completed = True
                break

    def is_reminded(self, username, key):
        if username not in self.reminders:
            self.reminders[username] = set()
        if key in self.reminders[username]:
            return True
        return False

    def mark_reminded(self, username, key):
        if username not in self.reminders:
            self.reminders[username] = set()
        self.reminders[username].add(key)