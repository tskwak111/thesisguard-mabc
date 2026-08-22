# Evaluation Harness

- `dataset/` : 시나리오별 DailyEvidencePack (examples 미러)
- `gold/`    : 골드 라벨 (`{case}.gold.json`) — expected_states, core_event_actions, expected_event_count

실행:

```bash
uv run thesisguard evaluate evaluation/dataset --gold evaluation/gold
```

지표와 예선 목표치는 `docs/product/2026-08-23-thesisguard-aaa-product-design.md` §20.2 기준이며,
계산 로직은 `src/thesisguard/evaluation/runner.py`, `metrics.py`에 있다.
표본 수(현재 9개 가상 시나리오)와 분모를 항상 함께 보고할 것.
