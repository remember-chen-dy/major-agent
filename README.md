# 高考专业推荐智能体

一款面向高考考生的 AI 志愿规划应用。通过自然对话式测评收集分数、位次、选科、性格、城市偏好、家庭资源等多维信息，结合大语言模型与实时网络搜索，为每位考生生成个性化的志愿规划报告。支持支付宝 9.9 元解锁完整报告，适合独立开发者快速上线运营。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
  - [后端](#后端)
  - [前端](#前端)
- [环境变量](#环境变量)
- [API 概览](#api-概览)
- [支付配置](#支付配置)
- [部署](#部署)
- [数据库管理](#数据库管理)
- [常见问题](#常见问题)
- [License](#license)

---

## 功能特性

- **对话式测评**：5 分钟自然对话完成信息采集，告别枯燥表单。
- **AI 志愿规划报告**：基于 LLM + DuckDuckGo 网络搜索，生成包含成绩定位、冲稳保院校、专业方向、避坑提醒、城市策略、行动清单的 Markdown 报告。
- **报告自动保存**：每次生成的报告自动存入 `reports` 表，支持历史回溯。
- **首页智能展示**：再次打开页面时自动读取 `userId`，展示最新报告；无报告则显示引导落地页。
- **报告库**：测评页右上角入口，按时间倒序查看所有历史报告。
- **支付解锁**：完整报告需支付 9.9 元，集成 ZPAY 支付宝支付网关，真实支付后解锁。
- **暖色极简 UI**：Tailwind CSS 定制暖色主题，移动端友好。
- **自动建表**：服务启动时自动创建数据库表，开箱即用。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS + Pinia + GSAP + Vue Router |
| 后端 | FastAPI + Pydantic Settings + SQLAlchemy 2.0（异步） |
| 数据库 | SQLite（默认）/ PostgreSQL |
| AI / 工作流 | LangGraph + LangChain + OpenAI 兼容接口 |
| 支付 | ZPAY / xpay 支付宝网关 |
| 部署 | Docker |

---

## 项目结构

```
major-agent/
├── backend/                       # FastAPI 后端
│   ├── api/                       # API 路由
│   │   ├── assessment_api.py      # 测评会话/聊天/结果接口
│   │   ├── auth.py                # 设备登录、用户信息
│   │   ├── reports.py             # 报告保存/查询/支付/回调接口
│   │   └── sessions.py            # 会话 CRUD
│   ├── config/                    # 配置初始化
│   │   ├── database.py            # SQLAlchemy 异步引擎与自动建表
│   │   └── llm.py                 # LLM 客户端初始化
│   ├── core/                      # 核心模块
│   │   ├── config.py              # Pydantic Settings 配置
│   │   ├── dependencies.py        # FastAPI 依赖
│   │   └── security.py            # X-Device-ID 认证
│   ├── models/                    # 数据模型
│   │   ├── report.py              # reports 表
│   │   ├── session.py             # sessions 表
│   │   └── user.py                # users 表
│   ├── services/                  # 业务服务
│   │   ├── assessment_service.py  # 测评流程服务
│   │   ├── report_service.py      # 报告生成与保存服务
│   │   ├── storage.py             # 对象存储/文件服务
│   │   └── xpay_service.py        # ZPAY 支付网关封装
│   ├── workflow/                  # LangGraph 工作流
│   │   ├── final_agent.py         # ReWOO 三节点报告生成
│   │   ├── graph.py               # 测评状态机图
│   │   ├── pdf_generator.py       # PDF 报告生成
│   │   ├── questions.py           # 问题配置
│   │   └── state.py               # 状态类型定义
│   ├── clear_db.py                # 清空数据库脚本
│   ├── Dockerfile                 # 后端容器镜像
│   ├── main.py                    # FastAPI 入口
│   ├── pyproject.toml             # Python 项目元数据
│   ├── requirements.txt           # Python 依赖
│   └── uv.lock                    # uv 锁定文件
├── frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── api/index.ts           # 统一 API 调用封装
│   │   ├── assets/main.css        # 全局样式
│   │   ├── stores/                # Pinia 状态管理
│   │   │   ├── auth.ts            # 用户认证 / deviceId
│   │   │   └── session.ts         # 会话状态
│   │   ├── views/                 # 页面组件
│   │   │   ├── Home.vue           # 首页/报告展示/落地页
│   │   │   ├── Assessment.vue     # 测评对话页
│   │   │   ├── Report.vue         # 完整报告页
│   │   │   ├── ReportLoading.vue  # 报告生成中页
│   │   │   └── ReportUnlock.vue   # 支付解锁页
│   │   ├── App.vue                # 根组件
│   │   ├── main.ts                # 入口（路由注册）
│   │   └── vite-env.d.ts          # Vite 类型声明
│   ├── index.html
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts             # Vite + 代理配置
└── README.md                      # 本文件
```

---

## 快速开始

### 后端

1. 进入后端目录并创建虚拟环境：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 创建 `.env` 文件：

```bash
cp .env.example .env
# 或手动创建 backend/.env，内容见下方「环境变量」章节
```

4. 启动服务：

```bash
python main.py
```

服务默认监听 `http://localhost:8000`，启动时会自动创建数据库表。

### 前端

1. 进入前端目录：

```bash
cd frontend
```

2. 安装依赖（推荐 pnpm）：

```bash
pnpm install
```

3. 启动开发服务器：

```bash
pnpm dev
```

开发服务器默认监听 `http://localhost:3000`，并通过 Vite 代理将 `/api` 请求转发到 `http://localhost:8000`。

---

## 环境变量

在后端目录创建 `.env` 文件，最小可运行配置如下：

```env
# 数据库（SQLite 示例，默认开箱即用）
DATABASE_URL=sqlite+aiosqlite:///./app.db

# LLM（OpenAI 兼容接口，支持 DeepSeek / OpenAI 等）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# CORS（开发环境可保留默认值）
CORS_ORIGINS=["*"]
```

完整配置项说明：

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | 是 | - | 数据库连接字符串，SQLite 或 PostgreSQL |
| `OPENAI_API_KEY` | 是 | - | LLM API 密钥 |
| `OPENAI_BASE_URL` | 否 | - | LLM API 基础 URL |
| `LLM_MODEL` | 否 | `gpt-4o` | 模型名称 |
| `CORS_ORIGINS` | 否 | `["*"]` | 允许的跨域来源 |
| `HOST` | 否 | `0.0.0.0` | 后端监听地址 |
| `PORT` | 否 | `8000` | 后端监听端口 |
| `DEBUG` | 否 | `False` | 调试模式 |
| `XPAY_GATEWAY_URL` | 否 | `https://zpayz.cn/` | ZPAY 支付网关 |
| `XPAY_PID` | 否 | - | ZPAY 商户 ID |
| `XPAY_KEY` | 否 | - | ZPAY 商户密钥 |
| `XPAY_REPORT_AMOUNT` | 否 | `9.90` | 报告解锁金额 |
| `XPAY_REPORT_NAME` | 否 | `高考志愿规划报告解锁` | 支付商品名称 |
| `XPAY_SITE_NAME` | 否 | - | 支付页面站点名称 |
| `PAYMENT_PUBLIC_BASE_URL` | 否 | - | 支付回调可访问的后端公网地址 |

> 提示：生产环境必须配置 `PAYMENT_PUBLIC_BASE_URL` 为后端公网地址，否则 ZPAY 回调无法到达。

---

## API 概览

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 根据 `device_id` 创建或获取用户 |
| GET | `/api/users/me` | 获取当前用户信息 |

### 测评

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assessment/session` | 创建新测评会话 |
| POST | `/api/assessment/chat/{session_id}` | 提交答案，获取下一问题或报告 |
| GET | `/api/assessment/session/{session_id}/results` | 获取会话最终结果 |

### 报告

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/reports` | 保存报告到 reports 表 |
| GET | `/api/users/{user_id}/reports/latest` | 获取用户最新报告 |
| GET | `/api/users/{user_id}/reports` | 获取用户所有历史报告 |
| GET | `/api/reports/by-session/{session_id}` | 按会话 ID 获取报告 |
| POST | `/api/reports/{report_id}/pay` | 创建支付宝支付订单 |
| GET | `/api/reports/{report_id}/payment-status` | 查询报告支付状态 |
| GET/POST | `/api/payments/xpay/notify` | ZPAY 异步回调 |
| GET/POST | `/api/payments/xpay/return` | ZPAY 页面跳转通知 |

---

## 支付配置

1. 注册 ZPAY（xpay）商户，获取 `PID` 和 `KEY`。
2. 在 `backend/.env` 中配置：

```env
XPAY_PID=your_pid
XPAY_KEY=your_key
PAYMENT_PUBLIC_BASE_URL=https://your-domain.com
```

3. 报告解锁金额默认为 9.9 元，可通过 `XPAY_REPORT_AMOUNT` 修改。
4. 确保 `PAYMENT_PUBLIC_BASE_URL` 指向的后端公网地址可以接收 ZPAY 回调。

---

## 部署

### Docker 部署后端

```bash
cd backend
docker build -t major-agent-backend .
docker run -d -p 8000:8000 --env-file .env --name major-agent-backend major-agent-backend
```

### 生产环境前端构建

1. 在前端目录创建 `.env.production`：

```env
VITE_API_BASE=https://your-domain.com
```

2. 构建并部署静态文件：

```bash
cd frontend
pnpm build
```

构建产物位于 `frontend/dist/`，可部署到任意静态托管服务或 Nginx。

### Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 数据库管理

### 自动建表

后端启动时会自动执行 `Base.metadata.create_all()`，无需手动迁移。

### 清空数据库

开发或测试需要清空全部数据时，使用提供的脚本：

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./app.db python clear_db.py
```

按提示输入 `yes` 后，脚本会删除并重建所有表。**生产环境慎用。**

> 注意：如果后端进程正在占用 SQLite 文件，需先停止服务再执行清空。

---

## 常见问题

### 前端请求后端接口报 404

- 确认后端服务已启动且监听 `8000` 端口。
- 确认 `vite.config.ts` 中代理配置正确指向 `http://localhost:8000`。
- 生产环境确认 `VITE_API_BASE` 配置正确。

### 首页提示「加载报告失败」

- 确认 `backend/.env` 中 `DATABASE_URL` 已配置。
- 查看后端日志确认数据库已正确初始化。
- 确认用户已完成 `authStore.login()` 且 `userId` 已写入 localStorage。

### 支付后状态未更新

- 确认 `PAYMENT_PUBLIC_BASE_URL` 为公网可访问地址。
- 查看后端日志确认收到 ZPAY 回调。
- 确认 `XPAY_PID` 和 `XPAY_KEY` 正确。

### 跨域错误

- 开发环境：Vite 代理已处理跨域。
- 生产环境：在 `backend/.env` 中正确配置 `CORS_ORIGINS`，例如 `["https://your-domain.com"]`。

### 报告生成失败

- 确认 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 可用。
- 查看后端日志确认 LLM 调用与 DuckDuckGo 搜索是否正常。
- 网络搜索不稳定时，系统会自动降级为规则化分析。

---

## License

[MIT](LICENSE)
