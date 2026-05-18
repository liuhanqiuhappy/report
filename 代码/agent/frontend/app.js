const API = '/api';
let token = '';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    login();
    initEventListeners();
});

// 模拟登录
async function login() {
    try {
        const res = await fetch(`${API}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: 'demo', password: '123'})
        });
        const data = await res.json();
        token = data.token;
        loadSidebarData();
        startReminderPolling();
    } catch (error) {
        console.error('登录失败:', error);
        showModal('登录失败', '无法连接到服务器，请检查网络连接');
    }
}

// 初始化事件监听
function initEventListeners() {
    // 侧边栏展开/收起
    document.getElementById('collapse-btn').addEventListener('click', toggleSidebar);
    document.getElementById('expand-btn').addEventListener('click', toggleSidebar);
    
    // 发送消息
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('user-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // 图片上传
    document.getElementById('image-upload').addEventListener('change', handleImageUpload);
    
    // 头部按钮
    document.getElementById('refresh-btn').addEventListener('click', loadSidebarData);
    document.getElementById('clear-btn').addEventListener('click', clearMessages);
    
    // 弹窗关闭
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('modal-confirm').addEventListener('click', closeModal);
    document.getElementById('modal-snooze').addEventListener('click', () => {
        closeModal();
        showModal('提醒已推迟', '一小时后将再次提醒您');
    });
}

// 切换侧边栏
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const expandBtn = document.getElementById('expand-btn');
    
    if (sidebar.classList.contains('collapsed')) {
        sidebar.classList.remove('collapsed');
        expandBtn.style.display = 'none';
    } else {
        sidebar.classList.add('collapsed');
        expandBtn.style.display = 'flex';
    }
}

// 加载侧边栏数据
async function loadSidebarData() {
    await Promise.all([
        fetchTodayCourses(),
        fetchTasks()
    ]);
}

// 获取今日课程
async function fetchTodayCourses() {
    try {
        const res = await fetch(`${API}/courses/today?token=${token}`);
        const data = await res.json();
        renderCourses(data.courses || []);
    } catch (error) {
        console.error('获取课程失败:', error);
    }
}

// 渲染课程列表
function renderCourses(courses) {
    const container = document.getElementById('course-list');
    
    if (!courses || courses.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无课程</div>';
        return;
    }
    
    container.innerHTML = courses.map(course => `
        <div class="course-card">
            <h4>${course.name}</h4>
            <div class="course-time">⏰ ${course.start_time} - ${course.end_time}</div>
            <div class="course-location">📍 ${course.location}</div>
        </div>
    `).join('');
}

// 获取任务列表
async function fetchTasks() {
    try {
        const res = await fetch(`${API}/tasks/uncompleted?token=${token}`);
        const data = await res.json();
        renderTasks(data.tasks || []);
    } catch (error) {
        console.error('获取任务失败:', error);
    }
}

// 渲染任务列表
function renderTasks(tasks) {
    const container = document.getElementById('task-list');
    const countEl = document.getElementById('task-count');
    
    countEl.textContent = tasks.length;
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无任务</div>';
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-card ${task.completed ? 'completed' : ''}" data-task-id="${task.id}">
            <div class="task-checkbox ${task.completed ? 'checked' : ''}" onclick="toggleTask('${task.id}', this)"></div>
            <div class="task-content">
                <div class="task-title">${task.title}</div>
                <div class="task-deadline">⏰ ${task.deadline}</div>
                ${task.course ? `<div class="task-course">📚 ${task.course}</div>` : ''}
            </div>
        </div>
    `).join('');
}

// 切换任务状态
async function toggleTask(taskId, checkbox) {
    const isChecked = checkbox.classList.toggle('checked');
    const taskCard = checkbox.parentElement;
    
    if (isChecked) {
        taskCard.classList.add('completed');
        try {
            await fetch(`${API}/tasks/complete?token=${token}&task_id=${taskId}`, {method: 'PUT'});
            fetchTasks();
        } catch (error) {
            console.error('更新任务失败:', error);
            checkbox.classList.remove('checked');
            taskCard.classList.remove('completed');
        }
    }
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    
    if (!text) return;
    
    addUserMessage(text);
    input.value = '';
    
    if (text.toLowerCase() === '课程') {
        await fetchTodayCourses();
        addBotMessage('已刷新今日课程列表，查看左侧边栏');
    } else if (text.toLowerCase() === '任务') {
        await fetchTasks();
        addBotMessage('已刷新待办事项，查看左侧边栏');
    } else if (text.toLowerCase() === '计划') {
        addBotMessage('📋 学习计划功能正在开发中...');
    } else if (text.toLowerCase() === '明天') {
        await fetchTomorrowCourses();
    } else {
        // 调用AI聊天接口
        await sendChatMessage(text);
    }
}

// 调用AI聊天接口
async function sendChatMessage(text) {
    try {
        const res = await fetch(`${API}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({token: token, prompt: text})
        });
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        const data = await res.json();
        
        if (data.response) {
            addBotMessage(data.response);
        } else {
            addBotMessage('获取响应失败，请重试');
        }
    } catch (error) {
        console.error('聊天失败:', error);
        addBotMessage('聊天失败，请检查网络连接');
    }
}

// 快捷命令
function sendQuickCommand(cmd) {
    document.getElementById('user-input').value = cmd;
    sendMessage();
}

// 添加用户消息
function addUserMessage(text) {
    const container = document.getElementById('chat-messages');
    const message = document.createElement('div');
    message.className = 'message user-message';
    message.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <div class="message-bubble">
                <p>${text}</p>
            </div>
        </div>
    `;
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

// 添加机器人消息
function addBotMessage(text) {
    const container = document.getElementById('chat-messages');
    const message = document.createElement('div');
    message.className = 'message bot-message';
    message.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-bubble">
                <p>${text}</p>
            </div>
        </div>
    `;
    container.appendChild(message);
    container.scrollTop = container.scrollHeight;
}

// 获取明天课程
async function fetchTomorrowCourses() {
    try {
        const res = await fetch(`${API}/courses/tomorrow?token=${token}`);
        const data = await res.json();
        
        if (data.courses && data.courses.length > 0) {
            let msg = '📅 明天课程：\n';
            data.courses.forEach(course => {
                msg += `${course.name} ${course.start_time}-${course.end_time} @ ${course.location}\n`;
            });
            addBotMessage(msg);
        } else {
            addBotMessage('明天没有课程');
        }
    } catch (error) {
        console.error('获取明天课程失败:', error);
        addBotMessage('获取明天课程失败，请稍后重试');
    }
}

// 处理图片上传
async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    addUserMessage('上传了截图，正在识别...');
    
    const type = confirm('是课表截图吗？选择"确定"为课表，"取消"为任务截图。') ? 'course' : 'task';
    const formData = new FormData();
    formData.append('token', token);
    formData.append('image', file);
    
    const url = type === 'course' ? `${API}/courses/import` : `${API}/tasks/import`;
    
    try {
        const res = await fetch(url, { method: 'POST', body: formData });
        
        // ✅ 新增：检查 HTTP 状态
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        
        const data = await res.json();
        addBotMessage('✅ 识别成功！已添加 ' + (type === 'course' ? data.courses?.length || 0 : data.tasks?.length || 0) + ' 条记录');
        
        if (type === 'course') {
            await fetchTodayCourses();
            addBotMessage('课程表已更新，查看左侧边栏');
        } else {
            await fetchTasks();
            addBotMessage('任务列表已更新');
        }
    } catch (error) {
        console.error('图片识别失败:', error);
        addBotMessage('❌ 图片识别失败：' + error.message);
    }
    
    e.target.value = '';
}

// 轮询提醒
function startReminderPolling() {
    setInterval(async () => {
        if (!token) return;
        
        try {
            const res = await fetch(`${API}/reminders?token=${token}`);
            const data = await res.json();
            
            data.reminders.forEach(r => {
                if (r.type === 'course') {
                    showModal('上课提醒', `${r.course_name} 将在${r.delta_minutes}分钟后开始，地点：${r.location}。`);
                } else if (r.type === 'task_deadline') {
                    showModal('任务提醒', `任务"${r.title}"即将截止！`);
                }
            });
        } catch (error) {
            console.error('获取提醒失败:', error);
        }
    }, 30000);
}

// 显示弹窗
function showModal(title, message) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = `<p>${message}</p>`;
    document.getElementById('modal-overlay').style.display = 'flex';
}

// 关闭弹窗
function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// 清空消息
function clearMessages() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-bubble">
                    <p>你好！我是你的校园学习助手。</p>
                    <p>有什么我可以帮你的吗？</p>
                </div>
            </div>
        </div>
    `;
}