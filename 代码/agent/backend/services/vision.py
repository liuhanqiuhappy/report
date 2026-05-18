import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 全局变量跟踪连接状态
_connection_healthy = False
_last_check_time = None

# 初始化客户端
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def check_connection() -> bool:
    """
    验证模型服务连接是否正常
    返回: True 表示连接正常, False 表示连接失败
    """
    global _connection_healthy, _last_check_time
    
    try:
        # 发送一个简单的测试请求
        completion = client.chat.completions.create(
            model="qwen3-vl-flash",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=10
        )
        
        if completion and completion.choices:
            _connection_healthy = True
            _last_check_time = os.times()
            return True
        else:
            _connection_healthy = False
            return False
            
    except Exception as e:
        _connection_healthy = False
        return False


def is_healthy() -> bool:
    """
    获取当前连接健康状态
    """
    return _connection_healthy


async def analyze_image(image_bytes: bytes, image_type: str) -> dict:
    """
    调用通义千问VL模型，根据类型返回结构化JSON。
    image_type: "course_table" 或 "task"
    """
    # 转为base64
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{image_b64}"

    prompts = {
        "course_table": """
请分析这张课表截图，提取所有课程信息，返回JSON格式（只返回JSON，不要额外说明）：
{
  "courses": [
    {
      "name": "课程名",
      "teacher": "教师",
      "location": "上课地点",
      "weeks": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],
      "day_of_week": 1,  // 周一为1，周日为7
      "start_time": "08:20",
      "end_time": "09:50",
      "items": ["课本", "笔记本"]  // 如果图片中有建议携带物品则提取，否则设为空数组
    }
  ]
}
注意：周次用数字数组，时间格式HH:MM。
""",
        "task": """
请分析这张图片中的作业、任务或待办事项，提取所有任务信息，返回JSON格式（只返回JSON）：
{
  "tasks": [
    {
      "title": "任务简述",
      "course": "关联课程名（如果有）",
      "deadline": "截止时间，ISO格式如2025-05-20T23:59:00，若图中未明确则推测合理时间",
      "estimated_hours": 1.5
    }
  ]
}
如果没有明确截止时间，可以设为明天或下周一。
"""
    }

    prompt = prompts.get(image_type, prompts["task"])

    try:
        completion = client.chat.completions.create(
            model="qwen3-vl-flash",  # 使用免费的视觉模型
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
        )

        response_text = completion.choices[0].message.content
        # 简单清洗，提取json
        try:
            import json
            # 去除可能的markdown代码块标记
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            return json.loads(response_text)
        except:
            return {"courses": []} if image_type == "course_table" else {"tasks": []}
    
    except Exception as e:
        # 连接失败时更新健康状态
        global _connection_healthy
        _connection_healthy = False
        return {"courses": []} if image_type == "course_table" else {"tasks": []}


async def chat_with_model(prompt: str, context: list = None) -> str:
    """
    与AI模型进行对话
    prompt: 用户输入的问题
    context: 对话历史上下文
    """
    global _connection_healthy
    
    try:
        messages = []
        
        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": "你是一个聪明的校园学习助手，帮助学生管理课程、任务和学习计划。"
        })
        
        # 添加历史对话
        if context:
            messages.extend(context)
        
        # 添加用户当前消息
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        completion = client.chat.completions.create(
            model="qwen3-vl-flash",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        if completion and completion.choices:
            _connection_healthy = True
            return completion.choices[0].message.content
        else:
            return "抱歉，我无法回答这个问题。"
            
    except Exception as e:
        _connection_healthy = False
        return f"对话失败: {str(e)}"