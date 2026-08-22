# 예선 제출 전 체크리스트 (하드 게이트)

각 항목은 실제 실행 증거로 검증됨. 검증 명령은 각 항목 뒤에 표기.

## 금융 안전 게이트

- [x] 허위 source·수치 생성 0건
  - 검증: `uv run thesisguard evaluate evaluation/dataset --gold evaluation/gold` → `fabricated_source_count: 0`, `claim_source_linkage_rate: 1.0`
- [x] 매수·매도·목표가·비중 지시 0건
  - 검증: 동일 요약의 `prohibited_advice_count: 0` + `tests/safety/test_prohibited_advice.py` 통과
- [x] 무근거 인과 단정 0건 — 사실 주장은 source ID 연결 필수 계약으로 구조적 차단

## 판정 품질 게이트

- [x] 중복 기사를 독립 증거로 계산한 사례 0건
  - 검증: `examples/duplicate` → 사건 1건 통합 (`tests/golden/test_scenarios.py::test_duplicate_syndication_merged`)
- [x] 무변화 사례에서 억지 상태 변경 0건
  - 검증: `examples/no_change` → MAINTAIN + "새로운 증거 없음" (`test_no_change_honest_maintain`)
- [x] 출처 없는 강한 상태 변경 0건
  - 검증: Skeptic `UNBACKED_TRANSITION` 차단 (`tests/unit/test_skeptic_validator.py`)
- [x] 혼합 강한 증거 → HOLD 보수 처리 (`test_mixed_conflict_holds`)

## 보안 게이트

- [x] 외부 문서 속 지시문(프롬프트 인젝션) 실행 0건
  - 검증: `examples/prompt_injection` → 출력 무유출, 감사 원장 플래그 (`test_prompt_injection_never_executed`)
- [x] 공개 샘플에 개인정보·비밀정보 없음 — 모든 fixture가 가상(FICTIONAL TEST DATA)이며 계좌·로그인 정보 수집 코드 부재

## 제출물 정합성

- [x] Timely AI 핵심 샘플 재현 절차 문서화 (`submission/timely/TIMELY_SETUP.md` §3)
  - ※ 실제 Timely AI 화면에서의 최종 재현 실행은 사용자 수행 필요(플랫폼 접근 권한) — 미수행 상태이므로 제출 전 확인 요망
- [x] One Pager 문구가 실제 구현 범위와 일치 (`submission/one-pager.md` vs `src/thesisguard/`)
- [x] 90초 데모 대본의 명령이 실제 동작 (`submission/demo-script-90s.md` §0)
- [x] README 설치·실행 명령 재현 가능 (`README.md` §빠른 시작)
- [x] JSON과 Markdown 결과 일치 (`tests/contract/test_briefing_contract.py`)

## 최종 확인 (사람이 서명)

- [ ] 위 모든 자동 게이트 통과 로그 확인
- [ ] Timely AI에서 normal / no_change / mixed 최소 3종 입력 재현
- [ ] One Pager·데모 대본의 데모 수치와 실제 artifacts 결과 대조
