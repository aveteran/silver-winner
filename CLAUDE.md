# CLAUDE.md

## Project

多岗位通用简历智能评估与自动优化系统（Web端）

- **定位**: 毕业设计项目 — 跨行业简历智能评分 + 缺陷诊断 + 自动优化建议生成
- **核心理念**: 规则驱动（非LLM依赖），稳定可控，所有规则可配置可扩展
- **开发周期**: 6-8周

## Tech Stack

| 层 | 技术 | 说明 |
|----|------|------|
| 后端框架 | FastAPI + Uvicorn | 异步IO，自动生成Swagger文档（答辩演示用） |
| ORM | SQLAlchemy 2.0 | 操作SQLite |
| 认证 | python-jose (JWT) + passlib[bcrypt] | 双Token机制 |
| 文件解析 | pdfplumber + python-docx | PDF/Word文本提取 |
| 中文处理 | jieba | 分词 + 自定义词典 |
| 模板引擎 | Jinja2 | SSR渲染 |
| 前端 | Bootstrap 5.3 + ECharts 5 + htmx 2.0 | 响应式 + 可视化 + 轻量交互 |
| PDF导出 | WeasyPrint | HTML→PDF |
| 数据库 | SQLite | 零配置，文件级存储 |

## Directory Structure

```
resume-system/
├── app/
│   ├── main.py              # FastAPI入口，生命周期管理
│   ├── config.py             # 配置中心（数据库URL、密钥、路径）
│   ├── api/                  # 接口层
│   │   ├── deps.py           # 依赖注入（get_db, get_current_user）
│   │   └── v1/               # API v1路由模块
│   ├── core/                 # 核心业务引擎（算法核心）
│   │   ├── parser/           # PDF/Word解析
│   │   ├── extractor/        # 信息抽取（NER + 关键词匹配）
│   │   ├── scorer/           # 六维度加权评分引擎
│   │   ├── defect/           # 规则驱动缺陷检测
│   │   ├── optimizer/        # 模板驱动优化建议生成
│   │   └── exporter/         # PDF报告导出
│   ├── models/               # SQLAlchemy ORM模型
│   ├── services/             # 业务服务层（编排引擎+数据访问）
│   ├── tasks/                # 异步任务（FastAPI BackgroundTasks）
│   └── utils/                # 工具函数
├── data/                     # 上传文件 + SQLite数据库（gitignore）
├── static/                   # CSS/JS/图片
├── templates/                # Jinja2模板（含admin/子目录）
├── tests/                    # pytest + httpx
├── requirements.txt
├── run.py                    # 启动脚本
└── CLAUDE.md
```

## Architecture Principles

1. **分层清晰**: api(路由) → services(编排) → core(算法) → models(数据)，单向依赖
2. **规则驱动**: 评分、缺陷检测、优化建议全部基于可配置规则，不依赖外部LLM API
3. **模板优先**: 优化建议用占位符模板生成，LLM增强作为可选开关（默认关闭）
4. **异步处理**: 上传后立即返回task_id，前端轮询状态，避免阻塞
5. **职责单一**: 每个core子模块只做一件事（解析/抽取/评分/检测/优化/导出）

## Database (11 tables, SQLite)

- `users` — 用户认证，role区分user/admin
- `position_categories` — 5大岗位类别
- `positions` — 40+岗位库，关联category和keywords
- `position_keywords` — 岗位技能关键词，含weight和is_required
- `scoring_weights` — 按岗位配置六维度权重
- `resumes` — 简历记录，raw_text + structured_data(JSON)
- `scoring_results` — 六维度得分 + grade(S/A/B/C/D)
- `resume_defects` — 缺陷记录，关联规则和位置
- `optimization_suggestions` — 优化建议，含original_text和improved_example
- `defect_rules` — 缺陷规则库，condition_json + 描述/建议模板
- `history_records` — 操作审计日志

## Scoring Engine (核心算法)

六维度加权评分（总分100）：

```
completeness (0.20-0.25)  — 必填字段覆盖
experience   (0.25-0.35)  — 经历关键词命中 + TF-IDF相似度
skills       (0.15-0.25)  — 必备技能命中率
education    (0.10-0.15)  — 学历层次 + 专业相关性
expression   (0.10-0.15)  — 量化描述占比 + 动作动词
format       (0.05-0.10)  — 错别字/日期格式/标点规范
```

权重按岗位类别自适应：IT类侧重技能/经历，商务类侧重表达，教育类侧学历。

## Defect Detection (规则引擎)

规则结构: `{rule_id, category, condition_json, severity(HIGH/MEDIUM/LOW), description_template, suggestion_template}`

六大规则类别：信息缺失、描述薄弱、格式问题、逻辑问题、关键词缺失、篇幅问题。

## Optimization Generation (模板引擎)

流程: `缺陷类型 → 匹配优化模板 → 填充上下文占位符 → 生成自然语言建议`

每条建议包含：问题原因 + 修改建议 + 示范优化文案（可直接复制）

## API Conventions

- 基础路径: `/api/v1`
- 响应格式: `{"code": 200, "message": "success", "data": {...}}`
- 认证: Bearer JWT Token
- 分页参数: `?page=1&per_page=20`
- 管理接口需 `require_admin` 依赖注入

## Dev Commands

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（创建表 + 导入种子数据）
python -m app.database.init_db

# 启动开发服务器
python run.py
# 或
uvicorn app.main:app --reload --port 8000

# 访问
# 首页: http://localhost:8000
# API文档: http://localhost:8000/docs
# Swagger UI: http://localhost:8000/redoc

# 运行测试
pytest tests/ -v
```

## Implementation Order (优先级)

1. **Phase 1**: config.py → models/ → 数据库初始化 + 种子数据 → auth模块 → app/main.py骨架
2. **Phase 2**: core/parser/ → core/extractor/ → core/scorer/（评分引擎是整个系统的计算核心）
3. **Phase 3**: core/defect/ → core/optimizer/ → services/（编排层）
4. **Phase 4**: api/v1/ 全部端点 → templates/ 全部页面 → 前端交互
5. **Phase 5**: core/exporter/ → 异步任务 → 测试 → UI打磨

## Key Conventions

- **命名**: 文件名 snake_case，类名 PascalCase，函数名 snake_case
- **类型注解**: 所有函数必须标注参数类型和返回类型（FastAPI + Pydantic 原生支持）
- **中文注释**: 模块和复杂逻辑用中文注释，变量/函数名用英文
- **错误处理**: 解析失败不抛异常，返回空字符串或None；文件损坏给出友好提示
- **配置文件**: 敏感信息通过.env文件管理，不硬编码
- **模板复用**: 前端抽取base.html基础布局，子模板通过Jinja2继承
