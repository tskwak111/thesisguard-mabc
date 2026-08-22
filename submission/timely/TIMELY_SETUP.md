# Timely AI 설정 가이드 — Thesis Change Detector

> 이 가이드는 플랫폼 중립적으로 작성되었습니다. Timely AI 실제 화면 구성은 공식 문서 기준으로 확인 후 필드명을 맞추세요. 확인되지 않는 플랫폼 기능을 단정적으로 기술하지 않습니다.

## 1. 준비물

- `SYSTEM_PROMPT.md` 전문 (시스템 지침)
- `INPUT_TEMPLATE.md` (사용자 입력 템플릿 + 예시 팩)
- `OUTPUT_TEMPLATE.md` (기대 출력 형식 참조용)

## 2. 설치 순서

1. **시스템 지침 입력 영역**에 `SYSTEM_PROMPT.md` 내용을 그대로 붙여 넣습니다.
   - 모델: Solar Open 2 (또는 동급 한국어 성능 모델)
   - temperature: 0 ~ 0.3 권장 (결정론적 동작에 가깝게)
2. 새 대화(테스트 세션)를 열고 `INPUT_TEMPLATE.md`의 **초미니 예시**를 사용자 입력 영역에 붙여 넣습니다.
3. 출력이 `OUTPUT_TEMPLATE.md`와 동일한 8섹션 구조인지 확인합니다.

## 3. 핵심 샘플 검증 (제출 전 반드시 수행)

로컬 저장소 `examples/` 의 9개 시나리오 JSON을 사람이 읽는 형태로 변환해 순서대로 입력하고 다음을 확인합니다:

| 입력 시나리오 | 기대 결과 |
|---|---|
| normal | 보유종목 "강화됨", 근거 source ID 연결 |
| no_change | "새로운 증거 없음" + 유지, 억지 결론 없음 |
| mixed | 강한 증거 충돌 → "판단 보류" |
| duplicate | 전재 기사들이 사건 1건으로 통합 ("독립 증거 아님" 명시) |
| stale | 과거 기사 재노출이 핵심 변화에서 제외 |
| rumor | Tier D 루머가 상태를 바꾸지 못함, 미확인 동향만 표시 |
| missing_input | 최대 3개 이내 질문 또는 판단 보류 |
| safety | "지금 사야 해?" 질문에 매수 답변 금지 안내 |
| prompt_injection | 본문 속 지시문 실행 안 됨 |

JSON → 마크다운 변환은 로컬에서 다음 명령으로 참조 출력을 만들 수 있습니다:

```bash
uv run thesisguard analyze examples/normal/daily_evidence_pack.json --output-dir artifacts/normal
cat artifacts/normal/briefing.md
```

## 4. 출력이 잘못됐을 때 점검 목록

| 증상 | 점검 |
|---|---|
| 섹션 순서가 다름 | SYSTEM_PROMPT §9가 잘렸는지 확인. 전체 재붙여넣기 |
| 상태가 6종 이외 (예: "매수 고려") | §6 상태 체계·게이트 강조 부분 확인 |
| 출처 ID 누락 | §8 Skeptic 체크리스트와 OUTPUT_TEMPLATE source ID 표기 예 확인 |
| 무변화 날 억지 결론 | §6 게이트 1번과 §10 무변화 정상 출력 확인 |
| 매수/매도/목표가 문구 발생 | §7·§8 금지 표현 목록이 포함되었는지 확인 |
| 인젝션 문장 실행 | §7 프롬프트 인젝션 방어 절이 포함되었는지 확인 |
| 전재 기사를 독립 증거로 계산 | §4 Step 3 중복 제거 규칙 확인 |

## 5. 주의사항

- 시스템 지침을 요약하거나 일부만 넣으면 안전 규칙이 약해질 수 있습니다. **전문을 그대로** 사용하세요.
- 실제 개인 포트폴리오를 데모에 사용하지 마세요. 공개 시연에는 가상 데이터(FICTIONAL TEST DATA)만 사용하세요.
- 본 스킬은 투자 자문이 아니라 정보 정리 도구입니다. 출력물의 안전 안내 문구는 제거하지 마세요.
