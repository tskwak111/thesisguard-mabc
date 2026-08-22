# ThesisGuard — Thesis Change Detector

> 오늘 주가가 아니라, 내가 산 이유가 달라졌는지를 추적합니다.

MABC 2026 예선 스킬 **Thesis Change Detector**의 로컬 참조 구현입니다.
사용자의 투자논지와 오늘의 자료(공시·뉴스·시장지표)를 비교해 **새롭게 달라진 증거만** 선별하고, 결정론적 게이트로 투자논지 상태(6단계)를 판정하며, 근거가 연결된 브리핑(JSON + Markdown)과 감사 원장을 생성합니다.

네트워크와 API 키 없이 전체 기능을 실행할 수 있습니다.

## 빠른 시작

```bash
# 1) 설치 (Python 3.12+, uv 사용)
uv sync

# 2) 입력 팩 검증
uv run thesisguard validate examples/normal/daily_evidence_pack.json

# 3) 분석 실행 → briefing.json / briefing.md / audit.json 생성
uv run thesisguard analyze examples/normal/daily_evidence_pack.json --output-dir artifacts/normal

# 4) 안전 스캔
uv run thesisguard safety-check artifacts/normal/briefing.md

# 5) 평가 하네스 (9개 시나리오)
uv run thesisguard evaluate evaluation/dataset --gold evaluation/gold
```

`uv` 없이: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` 후 `python -m thesisguard.cli ...` 동등 동작. (`thesisguard` 콘솔 엔트리포인트도 제공)

## 시나리오 예시 (모두 가상 데이터 — FICTIONAL TEST DATA)

| 디렉터리 | 시나리오 | 기대 결과 |
|---|---|---|
| examples/normal | 공식 공시가 핵심 가정 강화 | STRENGTHENED |
| examples/no_change | 기사만 많고 신규 정보 없음 | MAINTAIN + "증거 없음" |
| examples/mixed | 강한 상반 증거 충돌 | HOLD |
| examples/duplicate | 보도자료 전재 6건 | 사건 1건 통합 |
| examples/stale | 과거 기사 재노출 | 핵심 변화 제외 |
| examples/rumor | 커뮤니티 루머(Tier D) | 상태 변경 없음 |
| examples/missing_input | 이전 상태 누락 | 최대 3질문 + HOLD |
| examples/safety | "지금 사야 해?" | 매수 답변 거부 안내 |
| examples/prompt_injection | 본문 속 지시문 | 실행 차단 + 플래그 기록 |

## 아키텍처 한눈에

```
DailyEvidencePack(JSON)
  └─ Orchestrator
     ├─ input_validation   필수 입력·스키마 검증 (최대 3질문)
     ├─ FixtureAnalysisEngine / PromptAnalysisEngine   사건 추출 port
     ├─ event_normalizer   fingerprint 중복 제거
     ├─ novelty_detector   NEW/UPDATE/REPEAT/RESURFACED
     ├─ evidence_mapper    concept tag 연결 + 방향 판정
     ├─ state_transition   결정론적 6상태 게이트 (Tier·직접성·충돌 규칙)
     ├─ risk_mapper        포트폴리오 공통 위험(정성 등급)
     ├─ skeptic_validator  주장-근거·중복·반대증거·시점 검증
     ├─ safety             금지 투자지시 필터 + 프롬프트 인젝션 방어
     └─ briefing_composer + audit_ledger   JSON/MD 브리핑 + 감사 원장
```

핵심 원칙:
- LLM은 사건 구조화 후보에만 사용하고 **최종 상태는 코드의 결정론적 게이트가 결정**
- Tier D 루머는 상태 변경 불가, 동일 보도자료 전재는 독립 증거 아님
- 무변화일 때 "새로운 증거 없음"이 정상 출력
- 모든 주요 주장에 source ID, JSON↔Markdown 일치 계약 테스트

## 개발

```bash
uv run pytest -q                                  # 전체 테스트
uv run pytest --cov=thesisguard --cov-report=term-missing
uv run ruff format . && uv run ruff check .
uv run mypy src                                   # strict
```

## Timely AI 제출 패키지

`submission/timely/` — SYSTEM_PROMPT.md(시스템 지침), INPUT_TEMPLATE.md, OUTPUT_TEMPLATE.md, TIMELY_SETUP.md.
`submission/one-pager.md`, `submission/demo-script-90s.md`, `submission/submission-checklist.md`.

## 문서

- 제품 설계서: docs/product/2026-08-23-thesisguard-aaa-product-design.md
- 구현계획: docs/superpowers/plans/2026-08-23-thesisguard-preliminary-implementation.md
- 추적표: docs/implementation/traceability-matrix.md
- 가정·의사결정: docs/implementation/assumptions-and-decisions.md
