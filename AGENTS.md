# AGENTS.md

## 项目目的
`grok-x-lead-monitor` 用于按时间窗口从 Grok 检索潜在线索，做过滤与打分后，输出 Markdown 报告到 `output/leads/`。

## 本地运行
1. 创建并安装依赖：
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -U pip
   .venv/bin/python -m pip install -e .
   .venv/bin/python -m pip install pytest
   ```
2. 准备环境变量：
   - 复制 `.env.example` 为 `.env`
   - 填写 `GROK_API_KEY`
3. 运行主程序：
   ```bash
   .venv/bin/python src/grok_x_lead_monitor/main.py
   ```

## 自动 `.env` 加载规则
- 当 `run_pipeline(env=None)`（默认路径）时：
  - 先读取进程环境变量 `os.environ`
  - 再读取当前工作目录下 `.env`
  - 仅补充未设置的键，不覆盖已存在环境变量
- 当显式传入 `run_pipeline(env=...)` 时：
  - 只使用传入的 `env`，不会读取 `.env`

## 当前默认策略
- 默认时间窗为最近 3 天：
  - `DEFAULT_WINDOW_MODE=relative`
  - `RELATIVE_LOOKBACK_HOURS=72`
- 导出列为：
  - `User Handle (@username)`
  - `Tweet Content Summary`
  - `Pain Point Tag`
  - `Intent Score (1-10)`
  - `Exact Tweet URL`

## 测试
执行：
```bash
.venv/bin/pytest -q
```

## 常见问题
1. `ModuleNotFoundError: grok_x_lead_monitor`
   - 未通过可编辑安装启动。执行 `.venv/bin/python -m pip install -e .`
2. `ModuleNotFoundError: httpx`
   - 依赖未安装。执行 `.venv/bin/python -m pip install -e .`
3. `ValueError: GROK_API_KEY is required when no client is injected`
   - `.env` 未配置 `GROK_API_KEY`，或当前工作目录不是项目根目录。
4. 运行后仅有表头且终端出现 `[WARN] Grok query failed ... Operation not permitted`
   - 当前执行环境网络被限制，无法访问 xAI API；代码会继续执行并导出空结果表。

## 输出文件
默认输出目录为 `output/leads`，文件名为当天日期（例如 `2026-04-08.md`）。
