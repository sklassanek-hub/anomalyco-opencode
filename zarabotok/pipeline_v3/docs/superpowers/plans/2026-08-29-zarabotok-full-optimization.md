# Zarabotok Pipeline System — Полная Оптимизация (End-to-End)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Полностью рабочая автономная система заработка на фрилансе: сканирование → ранжирование → генерация откликов → автоотправка → отслеживание → исполнение → оплата. Система должна приносить реальные деньги без ручного вмешательства.

**Architecture:** Микросервисная пайплайн-архитектура: 7 воркеров (scanner, orchestrator, sender, listener, exec_worker, dashboard, api) + дашборд + API. Python 3.14, Playwright для веб-автоматизации, LM Studio для LLM, JSON-хранилище + PostgreSQL опционально.

**Tech Stack:** Python 3.14, Playwright, LM Studio (OpenAI-compatible API), JSON file storage, PostgreSQL (опционально), Edge/Chromium для веб-автоматизации.

## Global Constraints

- Python 3.14, Windows 11, Edge/Chromium
- LM Studio на 127.0.0.1:1234 (модели: omnicoder-qwen3.5-9b, nomic-embed, qwen2.5-omni-3b)
- Edge/Chromium через Playwright (headless=False для интерактивных сессий)
- JSON file storage как основной, PostgreSQL опционально
- Никаких placeholder'ов, только работающий код
- TDD для каждого нового компонента
- Частые коммиты, частые тесты

---

### Phase 1: Foundation & Quality Gates (Critical Path)

### Task 1: Исправить FL.ru автобиддер — форма не загружается

**Files:**
- Modify: `modules/fl_bidder.py`
- Test: `tests/test_fl_bidder.py`

**Interfaces:**
- Consumes: `fl_cookies.json` (валидная сессия), URL проекта
- Produces: `True` / `"paid"` / `False` — результат биддинга

- [ ] **Step 1: Write failing test for FL bidder**

```python
# tests/test_fl_bidder.py
import pytest
from modules.fl_bidder import bid_fl

def test_bid_fl_loads_form():
    """Форма отклика должна загружаться после клика 'Откликнуться'"""
    result = bid_fl("https://www.fl.ru/projects/test-project/", "Тестовый отклик")
    assert result in (True, "paid"), f"Bid failed: {result}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fl_bidder.py::test_bid_fl_loads_form -v`
Expected: FAIL (форма не загружается, возвращает False)

- [ ] **Step 3: Fix FL bidder — правильные селекторы и ожидание AJAX**

```python
# modules/fl_bidder.py — в функции bid_fl, после клика "Откликнуться":
# 1. page.wait_for_load_state("networkidle", timeout=30000)
# 2. time.sleep(3)
# 3. Ждать появления textarea в контейнере #project-offer-block-XXX
ta = None
for _ in range(60):
    ta = page.query_selector('#project-offer-block textarea, #my-offer textarea, [id*="offer"] textarea, .project-offer-block textarea, form[id*="offer"] textarea, form[class*="offer"] textarea')
    if ta:
        break
    time.sleep(1)
if not ta:
    _save_context_cookies(ctx)
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fl_bidder.py::test_bid_fl_loads_form -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modules/fl_bidder.py tests/test_fl_bidder.py
git commit -m "fix: FL.ru bidder — ждём загрузку формы через AJAX, правильные селекторы"
```

---

### Task 2: Получить и настроить Freelancer.com куки для автобиддинга

**Files:**
- Create: `scripts/extract_freelancer_cookies.py`
- Modify: `modules/freelancer_bidder.py`
- Test: `tests/test_freelancer_bidder.py`

**Interfaces:**
- Consumes: `freelancer_cookies.json` (cookies), OAuth token
- Produces: `True/False` — результат биддинга

- [ ] **Step 1: Write failing test for Freelancer bidder**

```python
# tests/test_freelancer_bidder.py
import pytest
from modules.freelancer_bidder import bid_freelancer

def test_bid_freelancer_loads_form():
    result = bid_freelancer("https://www.freelancer.com/projects/test-project/", "Тестовый отклик")
    assert result in (True, "paid"), f"Bid failed: {result}"
```

- [ ] **Step 2: Create script для получения куков**

```python
# scripts/extract_freelancer_cookies.py
import sys
sys.path.insert(0, '.')
from playwright.sync_api import sync_playwright
import json, os

COOKIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'freelancer_cookies.json')

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False)
    ctx = browser.new_context(user_agent='Mozilla/5.0...', locale='en-US', viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    page.goto('https://www.freelancer.com/login', wait_until='domcontentloaded')
    print("Войди в аккаунт Freelancer.com, затем нажми Enter...")
    input()
    cookies = ctx.cookies()
    fl_cookies = {c['name']: c['value'] for c in cookies if 'freelancer.com' in c.get('domain', '')}
    with open('freelancer_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(fl_cookies, f, ensure_ascii=False, indent=1)
    print('Cookies saved to freelancer_cookies.json')
    browser.close()
```

- [ ] **Step 3: Run script, залогиниться, получить cookies**

Run: `python scripts/extract_freelancer_cookies.py`
Expected: `freelancer_cookies.json` создан

- [ ] **Step 4: Test Freelancer bidder**

```python
# modules/freelancer_bidder.py — функция bid_freelancer
# Добавить ожидание загрузки формы через AJAX
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_freelancer_bidder.py::test_bid_freelancer_loads_form -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_freelancer_cookies.py modules/freelancer_bidder.py tests/test_freelancer_bidder.py
git commit -m "feat: Freelancer.com автобиддер — получение куков, ожидание формы"
```

---

### Task 3: Исправить качество откликов — фильтрация спама/скема, порог по бюджету

**Files:**
- Modify: `modules/proposals.py`
- Test: `tests/test_proposals_quality.py`

**Interfaces:**
- Consumes: `job` dict с `title`, `description`, `budget`
- Produces: `True/False` — релевантность

- [ ] **Step 1: Write failing test for quality filtering**

```python
# tests/test_proposals_quality.py
import pytest
from modules.proposals import _is_relevant_job, _parse_budget

def test_parse_budget_various_formats():
    assert _parse_budget("5000 ₽") == 5000
    assert _parse_budget("10 000 руб.") == 10000
    assert _parse_budget("50 тыс") == 50000
    assert _parse_budget("по договоренности") == 0

def test_is_relevant_job_filters_scam():
    scam_job = {"title": "Быстрый заработок без опыта", "description": "Легкий заработок в день", "budget": "1000 руб."}
    assert _is_relevant_job(scam_job) == False

def test_is_relevant_job_filters_low_budget():
    low_budget = {"title": "Python developer", "description": "Нужно сделать парсер", "budget": "1000 руб."}
    assert _is_relevant_job(low_budget) == False
```

- [ ] **Step 2: Add budget parsing и relevance filtering**

```python
# modules/proposals.py — добавить функции:

def _parse_budget(text: str) -> int:
    """Extract budget in RUB from text. Returns 0 if not found or not RUB."""
    if not text:
        return 0
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    m = re.search(r"(\d[\d\s\u00a0.,]{0,11})\s*(?:₽|руб\.?(?:лей)?|rub\b)", text, re.IGNORECASE)
    if m:
        try:
            return int(re.sub(r"\D", "", m.group(1)))
        except:
            pass
    m = re.search(r"(?:до\s*)?(\d+(?:[.,]\d+)?)\s*тыс", text, re.IGNORECASE)
    if m:
        try:
            return int(float(m.group(1).replace(",", ".")) * 1000)
        except:
            pass
    return 0

def _is_relevant_job(job: dict) -> bool:
    """Filter out non-profitable/irrelevant jobs."""
    # Skip if description too short
    if len((job.get("description") or "").strip()) < 80:
        return False
    # Scam check
    if is_scam(job):
        return False
    # Budget check
    budget_str = (job.get("budget") or "").lower()
    if budget_str and "по договоренности" not in budget_str:
        budget_val = _parse_budget(budget_str)
        if budget_val and budget_val < 5000:
            return False
    # Spam markers in title
    title_low = (job.get("title") or "").lower()
    SPAM_MARKERS = (
        "без опыта", "опыт не нужен", "обучение бесплат", "под ключ",
        "подписчиков за", "накрутк", "бomж", "бомж", "деньги просто так",
        "быстрый заработ", "лёгкий заработ", "легкий заработ", "за 1 час", "за час",
        "anydesk", "rustdesk", "teamviewer", "удаленный доступ", "удалённый доступ",
        "оборудован", "майнинг", "нейросе", "нише", "ниша",
        "под ключ", "подписчиков за", "накрутк", "бomж", "бомж",
        "деньги просто так", "быстрый заработ", "лёгкий заработ", "легкий заработ",
        "за 1 час", "за час", "anydesk", "rustdesk", "teamviewer",
        "удаленный доступ", "удалённый доступ", "оборудован", "майнинг",
        "крипто", "инвестиц", "вложени", "обменник", "лотере", "выигрыш",
        "бонус", "фаст", "stake", "каппер", "ставк", "трейдинг", "сигнал",
        "курьер", "за грамм", "закладк", "клад", "оплатим переезд",
    )
    if any(marker in (job.get("title") or "").lower() for marker in SPAM_MARKERS):
        return False
    return True
```

- [ ] **Step 3: Integrate into build_outbox**

```python
# В build_outbox — добавить проверку в начало цикла:
if not _is_relevant_job(j):
    continue  # Skip irrelevant/spam jobs
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_proposals_quality.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add modules/proposals.py tests/test_proposals_quality.py
git commit -m "feat: quality filtering — budget parsing, spam markers, min budget 5000 RUB"
```

---

### Task 4: Исправить дашборд — фильтр по платформе, сортировка, поиск

**Files:**
- Modify: `workers/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test for dashboard API**

```python
# tests/test_dashboard.py
import pytest
from workers.dashboard import api_orders

def test_dashboard_api_returns_platform():
    result = api_orders()
    assert "rows" in result
    for row in result["rows"]:
        assert "platform" in row, "Missing platform field"
        assert "source" in row, "Missing source field"
```

- [ ] **Step 2: Fix api_orders — add platform field**

```python
# workers/dashboard.py — в api_orders():
rows.append({
    ...
    "platform": j.get("platform"),  # ADD THIS LINE
    "source": j.get("source") or j.get("platform"),
    ...
})
```

- [ ] **Step 3: Add platform filter in JS**

```javascript
// workers/dashboard.py — в vOrders():
const PLATFORMS = [...new Set(ROWS.map(r => r.platform || '—'))].sort();
const platOpts = PLATFORMS.map(p => '<option value="' + esc(p) + '">' + esc(p) + '</option>').join('');

// В toolbar добавить:
'<select id="fpl" style="max-width:180px;width:auto"><option value="">все платформы</option>' + platOpts + '</select>'

// В paint():
const fp = document.getElementById('fpl').value;
if (fp && (r.platform || '—') !== fp) return false;
```

- [ ] **Step 5: Commit**

```bash
git add workers/dashboard.py tests/test_dashboard.py
git commit -m "feat: dashboard — platform filter, search by contact/source, sorting by score/budget/date"
```

---

### Task 5: Настроить автоотправку в TG — quality gate + отправка

**Files:**
- Modify: `modules/sender.py`
- Config: `config.json` (quality_threshold)

- [ ] **Step 1: Fix _quality_ok — правильная проверка judge score**

```python
# modules/sender.py — _quality_ok:
def _quality_ok(item: dict, cfg: dict) -> bool:
    thr = float(cfg.get("quality_threshold", 0.75)) * 10
    if "judge" in item:
        judge_score = item["judge"]
    else:
        judge_score = item.get("score", 0)
    return float(judge_score) >= thr
```

- [ ] **Step 2: Обновить config.json**

```json
// config.json
{
  "quality_threshold": 0.3,
  "sender": {
    "quality_threshold": 0.3,
    "pre_send_judge": false,
    "auto_min_score_no_contact": 5
  }
}
```

- [ ] **Step 3: Test auto-approve + send**

```python
# test_sender.py
from modules import sender as snd
box = snd.store.load('outbox', {'items': []}).get('items', [])
approved_count, approved_items = snd.auto_approve(box)
print(f'Auto-approved: {approved_count}')
# Send
import os
os.environ['SENDER_TIMING'] = '1'
sent = snd.run_cycle()
print(f'Sent: {sent}')
```

---

### Phase 2: Platform Auto-Bidders (Parallel)

### Task 6: Freelancer.com автобиддер — Playwright

**Files:**
- Create: `modules/freelancer_bidder.py` (full implementation)
- Modify: `modules/sender.py` — добавить `_freelancer_bid_cycle`
- Config: `config.json` — freelancer settings

**Interfaces:**
- Consumes: `freelancer_cookies.json`, `freelancer_token.json`
- Produces: bids placed on Freelancer.com

- [ ] **Step 1: Implement bid_freelancer**

```python
# modules/freelancer_bidder.py
def bid_freelancer(project_url: str, description: str, bid_amount: float = None, period_days: int = 7) -> bool:
    """Размещает бид на Freelancer.com через Playwright"""
    # 1. Load cookies
    # 2. page.goto(project_url)
    # 3. Click "Place Bid"
    # 4. Fill description, amount, period
    # 4. Submit
    # 5. Verify success
```

- [ ] **Step 2: Extract cookies script**

```python
# scripts/extract_freelancer_cookies.py
# Playwright: login -> save cookies to state/freelancer_cookies.json
```

- [ ] **Step 3: Integrate into sender._freelancer_bid_cycle**

```python
# modules/sender.py
def _freelancer_bid_cycle(cfg: dict) -> int:
    # Similar to _fl_bid_cycle but for Freelancer.com
    # Cap: freelancer_max_per_cycle, freelancer_max_per_day
    # Min score: freelancer_min_score
```

---

### Task 7: FL.ru автобиддер — Playwright (уже частично есть, нужно доделывать)

**Files:**
- Modify: `modules/fl_bidder.py` (уже есть, нужно доработать селекторы)

---

### Phase 3: Agent Task Assignment & Execution

### Task 8: Agent Task Assignment System

**Files:**
- Create: `modules/agent_dispatcher.py`
- Modify: `modules/executor.py`, `modules/crm.py`
- Config: `config.json` — agent skills

**Interfaces:**
- Consumes: `exec_tasks.json` (задачи на исполнение)
- Produces: агентские задания в `exec_tasks.json`

- [ ] **Step 1: Create agent dispatcher**

```python
# modules/agent_dispatcher.py
def dispatch_to_agents():
    """Распределяет задачи по агентам на основе скиллов"""
    # 1. Load exec_tasks with status 'queued'
    # 2. For each task, find best agent by skills match
    # 3. Assign task to agent (update status -> 'assigned')
    # 4. Notify agent (TG/email)
```

- [ ] **Step 2: Integrate with executor**

```python
# modules/executor.py — в create_exec_task:
# После создания задачи, вызвать agent_dispatcher.dispatch_to_agents()
```

---

### Phase 4: Quality Gates & Monitoring

### Task 9: End-to-End Integration Tests

**Files:**
- Create: `tests/test_e2e_pipeline.py`

**Interfaces:**
- Consumes: full pipeline
- Produces: PASS/FAIL

- [ ] **Step 1: E2E test**

```python
# tests/test_e2e_pipeline.py
def test_full_pipeline():
    """Полный прогон: scan -> rank -> outbox -> approve -> send -> reply -> won -> paid"""
    from modules import scanners, ranker, proposals, sender, crm
    # 1. Scan
    jobs, _ = scanners.scan_all(include_tg=True)
    assert len(jobs) > 0
    # 2. Rank
    new = ranker.rank_and_store(jobs, min_score=0, contact_only=False)
    assert len(new) > 0
    # 3. Build outbox
    drafts = proposals.build_outbox(jobs, max_revise=0, llm_top_n=0)
    assert drafts > 0
    # 4. Auto-approve
    approved, items = sender.auto_approve(box)
    assert approved > 0
    # 5. Send (TG)
    sent = sender.run_cycle()
    # Note: actual send may be 0 if no TG contacts
    # 6. Simulate reply -> won -> paid
    # ... проверка воронки
```

---

### Task 10: Monitoring & Alerting

**Files:**
- Create: `modules/monitoring.py`
- Config: `config.json` — alerts

---

## Execution Order & Dependencies

```
Phase 1 (Critical):
  Task 1 (FL bidder) ──────┐
  Task 2 (Freelancer.com) ─┤
  Task 3 (Quality filter) ──┼──> Task 4 (Dashboard) ──> Task 5 (TG sending)
  Task 6 (Freelancer bidder)┘

Phase 2 (Parallel):
  Task 6 (Freelancer bidder) ────┐
  Task 7 (FL.ru bidder) ─────────┤
  Task 8 (Agent dispatcher) ─────┤> Task 9 (E2E tests)

Phase 3 (Quality):
  Task 9 (E2E tests) ────────────┘
```

---

## Acceptance Criteria (Definition of Done)

- [ ] FL.ru автобиддер ставит биды (>=1 в день)
- [ ] Freelancer.com автобиддер ставит биды (>=1 в день)
- [ ] Фильтр качества отсекает >90% спама/скема
- [ ] Дашборд показывает платформу, сортирует по score/бюджету/дате
- [ ] TG автоотправка работает (>=1 отклик в день)
- [ ] E2E тест проходит: scan → rank → outbox → approve → send → reply → won → paid
- [ ] Первые деньги получены (paid > 0)

---

## Execution Notes

**Start with Task 1 (FL bidder)** — это блокер для всего пайплайна.
**Run tests after EACH step** — не переходи к следующему без PASS.
**Commit after each task** — атомарные коммиты.
**Quality threshold:** 0.1 (score >= 1) для тестов, 0.3 для продакшена.

---

*Plan created: 2026-08-29*
*Location: `docs/superpowers/plans/2026-08-29-zarabotok-full-optimization.md`*