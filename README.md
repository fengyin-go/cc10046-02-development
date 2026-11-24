# 网络数据采集与RPA自动化平台

面向网页数据采集、自动化流程编排、解析规则管理、代理池调度与采集结果校验的数据采集工程平台

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8010/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5174/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8010`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 爬虫配置 | `crawler_config` | 爬虫配置 | 配置标识、起始地址、页面编码 |
| 解析规则 | `parser_rule` | 解析规则 | 规则标识、目标页面、字段选择器 |
| 代理池 | `proxy_pool` | 代理节点 | 节点标识、代理地址、代理协议 |
| Cookie管理 | `cookie_mgr` | Cookie会话 | 会话标识、来源站点、Cookie内容 |
| 限速控制 | `rate_limiter` | 限速策略 | 策略标识、目标站点、请求频率 |
| 抽取模板 | `extraction_template` | 抽取模板 | 模板标识、适用站点、列表选择器 |
| 数据校验器 | `data_validator` | 校验规则 | 规则标识、校验字段、校验类型 |
| 采集调度 | `crawl_schedule` | 调度任务 | 任务标识、关联配置、调度周期 |
| 结果存储 | `result_store` | 存储批次 | 批次标识、来源配置、采集时间 |
| 去重引擎 | `dedup_engine` | 去重策略 | 策略标识、业务键列、排序字段 |
| 字段映射 | `field_mapper` | 映射方案 | 方案标识、来源字段、目标字段 |
| 异常重试 | `error_retry` | 重试策略 | 策略标识、错误类型、重试次数 |
| 批次追踪 | `batch_tracker` | 采集批次 | 批次标识、调度任务、开始时间 |
| 导出通道 | `export_channel` | 导出任务 | 任务标识、来源批次、导出格式 |
| 采集审计 | `crawl_audit` | 审计记录 | 记录标识、操作类型、操作对象 |
| 来源认证 | `source_auth` | 认证凭证 | 凭证标识、来源站点、认证方式 |
| HTML清洗 | `html_cleaner` | 清洗模板 | 模板标识、适用站点、标签过滤 |
| 增量同步 | `incremental_sync` | 同步水位 | 水位标识、来源配置、增量字段 |

## 覆盖率验收

`/coverage` 页面（后端 `app/services/coverage_acceptance.py`）用**映射后**的采集
记录计算关键字段覆盖率，按来源独立判定阈值。它决定哪些采集数据可以交付，结果
存储的 `执行校验` 动作也只认这个结论。

口径约定：

- **有效行**：关键字段实际采到即为有效。价格为 `0` 的实采行有效；映射时用默认
  值补出的 `0` 不计入有效行，并计入缺值。缺值行数、缺值字段数在任何阈值结果下都
  会返回，审查员始终能看到实际缺了多少。
- **分来源阈值**：每个来源单独判断，阈值设为 90% 即 `threshold=90`。合并覆盖率只
  作参考，不能把未达标来源合并成可交付。批次只有在全部必需来源都达标时才
  `可交付`，否则返回 `readable_sources`（现在能读的已确认来源）、`blocked_sources`
  （未达标）和 `pending_sources`（还差哪个来源没提交）。
- **多次提交**：同一来源 `append` 追加提交，样本量和有效行数按“全部来源行 + 原始
  有效行”累加；`replace` 重新提交会整体替换该来源累计口径。每一轮都会留下不可变
  的验收记录，含当时的阈值、结果和交付范围，重新提交后仍可追溯最初的阈值记录。

演示批次 `BATCH-PRICE-2026-11-24`：主站 95/100（通过）、镜像站 1/5（未通过），
合并 96/105 虽达标但分来源冲突，批次不可交付；镜像站重新提交 5/5 后批次转为可
交付，验收历史里能同时看到两轮的完整交付范围。

主要接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/coverage/batches` | 验收批次列表 |
| POST | `/api/coverage/batches` | 登记验收批次（来源、阈值、关键字段） |
| GET | `/api/coverage/batches/{id}` | 批次当前各来源有效行数与交付结论 |
| GET | `/api/coverage/batches/{id}/deliverable` | 可交付结果（结果存储的闸门） |
| GET | `/api/coverage/batches/{id}/rounds` | 完整验收历史，可按来源筛选 |
| POST | `/api/coverage/batches/{id}/submit` | 提交来源样本（append / replace） |
| GET | `/api/coverage/records` | 覆盖率验收数据（一次提交一行） |
| POST | `/api/coverage/map` | 映射记录并返回覆盖率，不落库 |
| POST | `/api/coverage/compute` | 只算覆盖率汇总 |

交付链路 `POST /api/chains/delivery` 支持 `require_coverage=true`：先按覆盖率验收
判定，未达标批次落成 `校验未过` 且不生成导出任务。

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数据采集、爬虫与RPA
