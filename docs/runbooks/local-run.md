# Grok X Lead Monitor Local Runbook

## Prerequisites
- Python 3.12+
- Install dependencies:

```bash
python -m pip install -e .
```

## Environment
Copy the template and fill in your API key:

```bash
cp .env.example .env
```

Then load env vars in your shell:

```bash
set -a
source .env
set +a
```

## Run Once (Real API)

```bash
python -m grok_x_lead_monitor.main
```

Output path:
- `output/leads/YYYY-MM-DD.md`

## Dry Run (No API Key Required)
This uses a fake in-memory client and still runs the full local pipeline.

```bash
PYTHONPATH=src python scripts/dry_run_pipeline.py
```

## Cron (Daily 23:58 Asia/Shanghai)
Use shell path based on your environment.

```cron
58 23 * * * cd /Users/dmiwu/work/PythonProject/GoDitto-WhatsApp && set -a && source .env && set +a && /usr/bin/env python -m grok_x_lead_monitor.main >> output/cron.log 2>&1
```

## Relative Window Mode
For rolling windows, set:

```bash
export DEFAULT_WINDOW_MODE=relative
export RELATIVE_LOOKBACK_HOURS=24
python -m grok_x_lead_monitor.main
```
