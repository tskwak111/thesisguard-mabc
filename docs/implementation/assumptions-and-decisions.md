# Assumptions and Decisions

작성 기준: 메타프롬프트 §18 — 비차단적 애매함은 가장 보수적·최소 범위로 결정하고 기록.

## A-1. 저장소 초기 상태
문제: 저장소가 Git 저장소가 아니었음(문서 2개만 존재).
결정: `main` 브랜치로 init 후 기준 문서를 최초 커밋하고, 기능 브랜치 `codex/thesisguard-preliminary-v1`에서 작업. 사용자 미커밋 변경은 존재하지 않았으므로 삭제/덮어쓰기 위험 없음.

## A-2. 샘플 입력 형식 = JSON
메타프롬프트 §7는 YAML 또는 JSON 중 하나를 주 형식으로 하라고 함. 저장소 관례가 없으므로 표준라이브러리만으로 파싱 가능한 **JSON**을 주 형식으로 선택(pyyaml 의존성 회피). CLI 예시 경로의 `.yaml`은 `.json`으로 동등 대체(README에 명시).

## A-3. 사건 추출의 LLM 대체 어노테이션 (`event_facts`)
문제: 로컬 참조 구현은 네트워크/LLM 없이 실행해야 하나, 실제 사건 구조화는 LLM 몫이다.
결정: SourceDocument에 선택 필드 `event_facts[]`(발표 주체·행위·대상·시각·수치·concepts·polarity_hint·근거 인용)를 두고, 이것이 "분석 엔진(LLM)이 반환했을 엄격 JSON 결과"를 팩 저자가 제공하는 계약으로 동작하게 한다.
- FixtureAnalysisEngine: event_facts 있으면 그대로 EventCandidate 변환, 없으면 문서당 제목 기반 단일 후보(polarity=UNKNOWN) 생성 — 보수적.
- PromptAnalysisEngine: 주입된 `complete_fn`으로 실제 LLM 호출 가능(opt-in), 출력은 엄격 스키마 검증. SDK 추측 구현 없음.
영향: polarity_hint는 팩 저자가 제공하므로 상태 게이트는 여전히 코드가 결정론적으로 통제한다(강한 전환은 Tier/직접성/신규성 게이트로 재검증).

## A-4. 논지 연결 방식
concept tag 교집합 기반의 결정론 매칭. 사건 concepts ∩ 핵심가정/강화조건/재검토조건/추적지표 태그 → 각 연결 유형. 시맨틱 유사도(NLP)는 범위 밖.

## A-5. 상태 사다리와 1일 1단계 규칙
심각도 하락 축 MAINTAIN→WATCH→WEAKENED→REVIEW_REQUIRED에서 하루 1단계 초과 전환 금지(위반 시 한 단계 억제). 예외: Tier A DIRECT 신규 증거가 사용자 명시 재검토조건 직접 충족 시 REVIEW_REQUIRED 즉시 허용(설계 §14.2). STRENGTHENED/HOLD는 별도 축으로 처리.

## A-6. "독립적 증거" 정의
fingerprint가 다른 사건만 독립 증거로 계산. 동일 fingerprint 군집은 대표 출처 1건 + 중복 문서 목록으로 환산.

## A-7. RESURFACED 판정 기준
사건 발생/발행 시각이 `last_briefing_at`보다 3일 이상 이전인데 오늘 팩에 다시 나타나면 RESURFACED → 핵심 변화 제외. (상수, 코드에 명시)

## A-8. 가중치 검증
포트폴리오 비중 합계 >100% 또는 개별 범위 위반은 입력 오류로 거부(질문 아님).

## A-9. 종목 식별 혼동 방지
동일 stock_code에 서로 다른 stock_name이 pack 내에서 발견되면 입력 오류. 우선주/보통주는 별도 code 요구 — 이름 유사도 자동 판단은 하지 않고 코드 일치 원칙으로 보수적으로 처리.

## A-10. Jinja2 미사용
브리핑 Markdown은 문자열 빌더로 생성. 섹션 순서·헤더를 상수화해 JSON과의 계약 테스트로 일치 보장.

## A-11. Python 버전
`requires-python >=3.12`. 로컬 환경은 3.14 — uv로 관리된 venv에서 검증.

## A-12. 실제 LLM/Solar 연동 미구현
SDK 사양 확인 불가 → 추측 구현 금지(메타 §9). Timely AI용 프롬프트 산출물이 예선 실전 경로이며, 로컬 코드는 참조 구현+평가 하네스 역할.

## A-13. 우선주 표기 등 한국어 표시명
enum 내부값 영어, 사용자 표시명 한국어 매핑 테이블 단일 정의(`domain/enums.py`).

## A-14. 평가 코드 위치
메타프롬프트 권장 구조의 루트 `evaluation/metrics.py·runner.py`는 패키지 import 가능성을 위해 `src/thesisguard/evaluation/`으로 이동하고, 루트 `evaluation/`은 dataset·gold 데이터와 README만 유지.

## A-15. duplicate 시나리오 기대 상태 정정
동일 보도자료 전재 사건이 사용자의 명시적 재검토 조건(capex_cut)을 Tier A로 직접 충족하므로 WEAKENED가 아니라 REVIEW_REQUIRED가 설계 §14.6에 부합. 골드 라벨을 정정함(엔진 수정 아님).

## A-16. prompt_injection 시나리오 기대 상태
해당 팩의 유일한 긍정 근거는 Tier B 단일 출처라 STRENGTHENED 게이트(공식 또는 복수 확인)를 통과하지 못해 MAINTAIN이 보수적으로 올바름. 골드 라벨에 명시.

## A-17. 시장 맥락의 방향 필드
MarketContextItem.change_direction(POSITIVE/NEGATIVE/NEUTRAL/UNKNOWN)은 팩 저자가 제공하는 정성 방향이다. NEGATIVE인 경우에만 해당 위험요인 태그의 공통 위험 "오늘 악화" 표시에 사용되며, 상태 전환 게이트에는 들어가지 않는다(간접 거시 변화는 WATCH 상한 유지).

## A-18. 브리핑 품질 계약 (AAA 검증에서 추가)
- 보유·관심 종목 섹션은 "반대 또는 제한 증거" 라인을 항상 출력한다(없으면 "확인되지 않았습니다").
- 해석 문장은 "(해석)" 라벨로 사실과 구분한다.
- 오늘 한 줄은 개별 사건 문장을 반복하지 않는 포트폴리오 수준 요약이다.
- 논지 카드 없는 포트폴리오 종목은 조용히 생략하지 않고 최대 3질문으로 확인을 요청한다.
- user_question 중 매수·매도·비중·목표가 성격의 질문만 안전 거부 문구를 트리거한다.
