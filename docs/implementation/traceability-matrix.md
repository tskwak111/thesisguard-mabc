# Traceability Matrix — 설계서 ↔ 구현 ↔ 테스트

| 설계 요구사항 (출처) | 구현 | 테스트 | 문서/산출물 |
|---|---|---|---|
| DailyEvidencePack 입력 형식·필수 검증, 최대 3질문 (설계 §8.4–8.5, 메타 §7) | `domain/*.py`, `application/input_validation.py` | `tests/unit/test_input_validation.py`, `tests/golden/test_missing_input.py` | `submission/timely/INPUT_TEMPLATE.md` |
| Step1 입력 정규화(중복 source ID·해시·시각) (§8.6) | `application/orchestrator.py` `_normalize` | `tests/unit/test_input_validation.py::test_duplicate_source_ids_rejected` | 감사원장 `issues` |
| Step2 사건 추출(누가/무엇/언제/수치/출처) (§8.6) | `ports/analysis_engine.py`, `adapters/*` | `tests/unit/test_event_normalizer.py` | `prompts/event_extraction.md` |
| Step3 사건 중복 제거 — 전재 기사 1건 통합 (§8.6, §13.3) | `application/event_normalizer.py` fingerprint | `tests/unit/test_event_normalizer.py::test_press_release_syndication_merges_to_one_event` | 지표: 중복 제거 정확도 |
| Step4 신규성 NEW/UPDATE/REPEAT/RESURFACED (§8.6) | `application/novelty_detector.py` | `tests/unit/test_novelty_detector.py` | 골든 stale/no_change 시나리오 |
| Step5 논지 연결 5분류+무관 제외·감사기록 (§8.6) | `application/evidence_mapper.py` | `tests/unit/test_evidence_mapper.py` | 감사원장 exclusions |
| Step6 증거 방향 5종 + 평가축 8필드 (§8.6, §13.2, 메타 §5.3) | `domain/evidence.py` EvidenceLink | `tests/unit/test_evidence_mapper.py` | JSON 결과 evidence 블록 |
| Step7 결정론적 상태 전이 게이트, 6상태 (§14, 메타 §5.1/5.4) | `application/state_transition.py` | `tests/unit/test_state_transition.py` (강화/약화/혼합HOLD/루머무시/1일1단계/Tier D 차단) | `docs/implementation/assumptions-and-decisions.md` |
| Step8 포트폴리오 공통 위험 정성등급 (§15) | `application/risk_mapper.py` | `tests/unit/test_risk_mapper.py` | 브리핑 §5 섹션 |
| Step9 Skeptic 검증 10항목 (§8.6, 메타 §8 Step9) | `application/skeptic_validator.py` | `tests/unit/test_skeptic_validator.py` (주장-근거 불일치/반대증거누락/시점충돌) | 감사원장 skeptic_results |
| Step10 브리핑 8섹션 고정 순서·JSON 동일성 (§8.7, 메타 §5.5) | `application/briefing_composer.py` | `tests/contract/test_briefing_contract.py` | `submission/timely/OUTPUT_TEMPLATE.md` |
| 출처 등급 A/B/C/D 규칙, Tier C 단독 금지, Tier D 배제 (§13.1) | enums + state_transition 게이트 | `tests/unit/test_state_transition.py::test_tier_d_never_changes_state` | SYSTEM_PROMPT.md |
| 무변화 → MAINTAIN 정상 출력 (§5.5, 메타 §5.4) | state_transition | `tests/golden/test_no_change.py` | 데모 대본 2부 |
| 매수·매도·목표가·비중 지시 차단 (메타 §11.1) | `safety/prohibited_advice.py` | `tests/safety/test_prohibited_advice.py` (KR/EN/우회표현+허용사례) | 체크리스트 하드게이트 |
| 사용자 "사야 해?" 질문 처리 (메타 §11.2) | briefing_composer 안내 문구 | `tests/safety/test_user_buy_sell_question.py` | OUTPUT_TEMPLATE |
| 프롬프트 인젝션 데이터 처리 (§13.5, 메타 §11.3) | `safety/prompt_injection.py` + orchestrator | `tests/safety/test_prompt_injection.py`, `tests/golden/test_prompt_injection.py` | SYSTEM_PROMPT 방어 절 |
| 종목 식별 오류(우선주/유사명) 거부 (§19.1) | input_validation + orchestrator 코드-이름 정합 체크 | `tests/unit/test_entity_confusion.py` | INPUT_TEMPLATE 주의사항 |
| 시점 충돌 비교 금지 (§13.4, §19) | skeptic_validator `data_as_of_conflict` | `tests/unit/test_skeptic_validator.py` | 정보 품질 섹션 |
| 감사 원장 (§11.12, 메타 §8 Step10) | `application/audit_ledger.py` | `tests/contract/test_audit_ledger.py` | JSON 결과 audit 필드 |
| AnalysisEngine Port / 네트워크 없음 / Fixture 엔진 (메타 §9) | ports/adapters | 전체 테스트 스위트(오프라인) | TIMELY_SETUP.md |
| CLI validate/analyze/evaluate/safety-check (메타 §13) | `cli.py` | `tests/integration/test_cli.py` + smoke 실행 증거 | README |
| 평가 지표 10종 + 목표치 (§20.2, 메타 §12.2) | `src/thesisguard/evaluation/{metrics,runner}.py`, 데이터는 `evaluation/{dataset,gold}` | `tests/integration/test_evaluation.py` | `evaluation/README.md` |
| 가상 fixture FICTIONAL 표시 (메타 §12.1) | examples/* 모든 팩 | golden 테스트가 헤더 검증 | examples 헤더 |
| Timely 스킬 산출물 4종 (메타 §10) | submission/timely/* | 수동 검토 + 로컬 파이프라인과 계약 일치 확인 | 제출 패키지 |
| One Pager / 90초 데모 / 체크리스트 (메타 §14) | submission/*.md | 체크리스트 자체 검증 | 제출 패키지 |
| 결선 확장 경계 문서 (메타 §4.2) | docs/roadmap/final-mvp-roadmap.md | — | roadmap |
| 품질 게이트: ruff/mypy strict/pytest/cov (메타 §16) | pyproject 설정 | CI 워크플로 | README 재현 명령 |

| 시장 맥락 → 공통 위험 오늘의 변화 (§15.3) | `orchestrator.py` adverse_market_tags, `risk_mapper.py` | `tests/contract/test_briefing_contract.py::test_market_context_negative_marks_risk_deterioration` | INPUT_TEMPLATE MARKET_CONTEXT |
| 반대 증거 항상 표시·사실/해석 라벨·포트폴리오 헤드라인 (§5.3, §8.7) | `briefing_composer._stock_section`, `orchestrator._portfolio_headline` | `TestBriefingQualityContract` 7종 | OUTPUT_TEMPLATE |
| LLM 어댑터 엄격 JSON 계약 (메타 §9) | `adapters/prompt_analysis_engine.py` | `tests/unit/test_prompt_analysis_engine.py` | prompts/event_extraction.md |

미충족 항목: 없음 (단, "실제 LLM 연동"은 의도적으로 범위 제외 — assumptions 참조)
