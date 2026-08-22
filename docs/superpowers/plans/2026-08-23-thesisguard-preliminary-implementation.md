# ThesisGuard 예선 구현계획

- 작성일: 2026-08-23
- 기준 문서: `docs/product/2026-08-23-thesisguard-aaa-product-design.md` (v1.0), `docs/instructions/2026-08-23-thesisguard-implementation-meta-prompt.md`
- 브랜치: `codex/thesisguard-preliminary-v1`
- 목표: MABC 2026 예선 제출 가능한 **Thesis Change Detector** 참조 구현(로컬 결정론 파이프라인 + Timely AI 스킬 패키지)

## 1. 목표와 비목표

### 목표
1. DailyEvidencePack 입력 스키마 + 검증기 (JSON 주 형식)
2. 포트폴리오·투자논지·이전 상태·출처·사건·증거 도메인 모델
3. 사건 추출 계약, 사건 단위 중복 제거(fingerprint), 신규성 판정(NEW/UPDATE/REPEAT/RESURFACED)
4. 사건↔핵심 가정·강화 조건·재검토 조건 연결 (concept tag 매칭)
5. 증거 방향 판정(STRENGTHEN/WEAKEN/MIXED/NEUTRAL/UNKNOWN) 및 6단계 상태 결정론 전이 엔진
6. 포트폴리오 공통 위험 탐지(정성 등급)
7. Skeptic 검증기 + 금융 안전 출력 필터 + 프롬프트 인젝션 방어
8. JSON 결과 + Markdown 브리핑(8섹션 고정 순서) + 감사 원장
9. 로컬 CLI(validate / analyze / evaluate / safety-check)
10. 골든 테스트 + 평가 하네스 + 지표 계산기
11. Timely AI 시스템 지침·입력/출력 템플릿·설정 가이드
12. One Pager · 90초 데모 대본 · 제출 체크리스트

### 비목표 (설계서 §4.2 그대로)
실시간 API, 크롤링, 계좌연동, 자동매매, 종목추천, 목표가·수익률 예측, 웹 대시보드, 인증·DB·푸시, 미국주식·ETF·파생·가상자산. 실제 LLM SDK 연동(추측 구현 금지).

## 2. 파일 구조와 책임

메타프롬프트 §6.1 권장 구조를 따른다. 차이점:
- 템플릿은 Jinja2 대신 순수 문자열 빌더(`briefing_composer.py`) — 의존성 최소화
- 샘플 입력은 JSON 주 형식 (stdlib만 사용, pyyaml 의존성 회피)
- `adapters/prompt_analysis_engine.py`: 실제 SDK 호출 없이 주입된 `complete_fn`(callable)으로 동작하는 opt-in 어댑터

```text
src/thesisguard/
├── domain/            # enums, portfolio, thesis, sources, events, evidence, state, briefing (Pydantic v2, 불변 데이터)
├── application/       # input_validation, event_normalizer, novelty_detector, evidence_mapper,
│                      # state_transition, risk_mapper, skeptic_validator, briefing_composer,
│                      # audit_ledger, orchestrator (파이프라인 Step 1~10)
├── ports/analysis_engine.py        # AnalysisEngine Protocol
├── adapters/
│   ├── fixture_analysis_engine.py  # 결정론적 참조 엔진 (event_facts 구조화 어노테이션 소비)
│   └── prompt_analysis_engine.py   # LLM 주입형 어댑터 (엄격 JSON 스키마 검증)
├── safety/            # policy(패턴 상수), prohibited_advice, prompt_injection
└── cli.py             # argparse 기반 4개 하위명령
prompts/, submission/timely/, examples/<9 scenarios>/, evaluation/{dataset,gold,metrics.py,runner.py},
tests/{unit,contract,golden,safety,integration}/
```

## 3. 핵심 인터페이스 계약

### 입력 (DailyEvidencePack, Pydantic v2 strict)
```
schema_version="1.0", briefing_as_of(A tz datetime), first_run(bool),
portfolio[{stock_code, stock_name, market?, kind(HOLDING|WATCH), weight?(0..100)]}],
thesis_cards[{stock_code, summary, horizon?, approved_version,
  core_assumptions[{id, text, concept_tags[]}], strengthen_conditions[...],
  review_conditions[...], tracked_indicators[...], risk_factors[]}],
previous_states[{stock_code, state|FIRST_RUN, known_event_keys[], last_briefing_at?}],
market_context[{indicator, value_or_change, as_of, source_id, risk_factor_tags[]}],
today_sources[{source_id, publisher, url_or_id, doc_type(FILING|IR|NEWS|REPORT|SOCIAL),
  published_at, collected_at, as_of, tier(A|B|C|D), title, body, content_hash,
  event_facts?[{issuer, action, entities[], event_type, event_date, key_figures[],
                conditions?, concepts[], polarity_hint, quotes[]}]}]
```
- 필수 누락 시 → `ValidationIssue` 목록 + **최대 3개 질문**, 강한 결론 금지
- `event_facts`는 "LLM이 반환했을 구조화 결과"를 팩 저자가 제공하는 어노테이션이다(로컬 무네트워크 실행용; assumptions 문서 참조)

### 처리 파이프라인 (Orchestrator.run)
Step1 정규화(source ID 중복·해시·시각 체크) → Step2 사건 추출(engine.extract_events) → Step3 중복 제거(fingerprint = issuer|event_type|대상기업|날짜버킷|핵심수치 정규화) → Step4 신규성(known_event_keys, 발행일 vs last_briefing_at) → Step5 논지 연결(concept_tags ∩ 사건 concepts) → Step6 방향 판정(polarity_hint × 연결 대상 부호: 재검토조건 부정=긍정신호 등은 하지 않고 보수적으로 그대로, 강화조건 충족=STRENGTHEN 후보) → Step7 상태 게이트(state_transition) → Step8 공통 위험(risk_mapper) → Step9 Skeptic(skeptic_validator) → Step10 브리핑+원장(briefing_composer, audit_ledger)

### 상태 전이 규칙 (결정론, domain/enums + application/state_transition)
심각도 사다리: MAINTAIN(0) < WATCH(1) < WEAKENED(2) < REVIEW_REQUIRED(3); STRENGTHENED/HOLD는 별도 축.
1. 유효 신규 증거(NEW/UPDATE, Tier A/B/C, 관련 있음) 없음 → MAINTAIN
2. Tier D 또는 UNCONFIRMED만 있음 → MAINTAIN (미확인 동향 섹션에만 표시)
3. 강한 상반 증거(STRENGTHEN 강증거 ≥1 AND WEAKEN 강증거 ≥1, 강=Tier A 직접 또는 A/B 복수확인) → HOLD
4. 재검토조건 직접 충족 + Tier A DIRECT NEW/UPDATE → REVIEW_REQUIRED
5. STRENGTHENED 게이트: Tier A DIRECT 핵심가정 지지 NEW/UPDATE, 또는 독립 A/B MULTI_CONFIRMED 동방향, 또는 강화조건의 공식 충족 — 하나 이상 & 반대 강증거 없음
6. WEAKENED 게이트: Tier A/B DIRECT 반증 NEW/UPDATE
7. WATCH: 간접·저신뢰 부정 신호, 거시 악화
8. 1일 1단계 초과 전환 금지(단, 규칙4는 예외 허용) — 위반 시 한 단계 낮춤
9. Skeptic 치명 실패 → HOLD 또는 이전 상태

### AnalysisEngine Port
```python
class AnalysisEngine(Protocol):
    def extract_events(self, pack) -> list[EventCandidate]
    def map_evidence(self, events, theses) -> list[EvidenceCandidate]  # 후보만, 최종 아님
    def review_draft(self, draft) -> SkepticReview                     # 선택 보조검토
```

## 4. TDD 작업 순서 / 실패 테스트 / 커밋 경계

| # | 작업 | 먼저 작성할 실패 테스트 | 실행 명령 | 커밋 |
|---|---|---|---|---|
| C1 | 부트스트랩(pyproject, ruff/mypy/pytest 설정) | tests/test_smoke.py | `uv run pytest -q`, `uv run ruff check .` | `chore: bootstrap typed ThesisGuard package and quality gates` |
| C2 | 도메인 enum·모델 + DailyEvidencePack 검증기 | tests/unit/test_input_validation.py (누락 필드→질문≤3, tier D, 가중치 합, 중복 source ID, 시간대) | `uv run pytest tests/unit -q` | `feat: add Daily Evidence Pack domain contracts` |
| C3 | 사건 추출 계약·fingerprint 중복 제거·신규성 | tests/unit/test_event_normalizer.py, test_novelty_detector.py (동일 보도 20건→1사건, 수치 변경→UPDATE, 과거기사→RESURFACED) | 同上 | `feat: normalize events and detect novelty` |
| C4 | 증거 연결·방향 판정·상태 전이 게이트 | tests/unit/test_evidence_mapper.py, test_state_transition.py (14필수 시나리오 중 상태 규칙 8종) | 同上 | `feat: map evidence and enforce thesis state transitions` |
| C5 | 리스크 매퍼·Skeptic·안전 필터(금지지시/인젝션) | tests/unit/test_risk_mapper.py, test_skeptic_validator.py, tests/safety/* | 同上 + `uv run pytest tests/safety -q` | `feat: add portfolio risk and skeptic validation` |
| C6 | 브리핑 작곰(JSON/MD 일치)·감사 원장·오케스트레이터 | tests/contract/test_briefing_contract.py (섹션 순서, source ID 연결률 100%, JSON↔MD 일치) | 同上 | `feat: compose auditable JSON and markdown briefings` |
| C7 | CLI 4개 명령 + examples 9종 fixture | tests/integration/test_cli.py, tests/golden/* | `uv run thesisguard analyze examples/normal/daily_evidence_pack.json --output-dir artifacts/normal` | `test: add golden safety and adversarial scenarios` |
| C8 | 평가 하네스 + 지표 | evaluation/metrics.py 유닛테스트 | `uv run thesisguard evaluate ...` | `feat: add evaluation harness and sample datasets` |
| C9 | Timely/One Pager/데모/체크리스트/README/.env.example/.gitignore/CI | — | README 명령 재실행 | `docs: add Timely skill and contest submission package` |
| C10 | 전체 게이트 + 증거 수집 | — | 아래 §6 | `chore: verify release candidate and document evidence` |

## 5. 리스크와 롤백
- Python 3.14 환경에서 mypy/pydantic 호환 문제 → `requires-python >=3.12`, uv 고정 버전 사용; 실패 시 pydantic 최신 stable로 pin 조정
- 모듈 간 타입 불일치 → mypy strict를 C2부터 매 커밋 실행하여 조기 차단
- 롤백: 각 커밋이 독립 검증 가능하므로 `git revert <commit>` 단위 복구

## 6. 완료 검증 게이트 (§16 동등)
```bash
ruff format --check . && ruff check . && mypy src
pytest -q
pytest --cov=thesisguard --cov-report=term-missing
# CLI smoke: validate/analyze(normal,no_change,mixed)/evaluate/safety-check
```
하드 게이트(허위 출처 0, 금지지시 0, 중복 독립계산 0, 무변화 억지전환 0, 무근거 강한전환 0, 외부지시 실행 0, JSON↔MD 일치) 통과 시에만 확정.

## 7. 추적표
`docs/implementation/traceability-matrix.md` 참조 (설계서 §8·§13·§14·§16·§20 ↔ 모듈/테스트/문서 매핑).
