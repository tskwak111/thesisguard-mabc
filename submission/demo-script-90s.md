# 90초 데모 대본 — Thesis Change Detector

> 준비물: `examples/normal`, `examples/no_change`, `examples/duplicate` 팩과 미리 생성한 `artifacts/normal/briefing.md` 출력. 실시간 실행이 실패할 경우 미리 캡처한 결과 화면으로 대체합니다(§5).

## 0. 사전 준비 (데모 전 완료)

```bash
uv sync
uv run thesisguard analyze examples/normal/daily_evidence_pack.json --output-dir artifacts/normal
uv run thesisguard analyze examples/no_change/daily_evidence_pack.json --output-dir artifacts/no_change
```

## 1. (0~15초) 문제 제기 — 화면: 투자논지 카드

**[화면]** `examples/normal/daily_evidence_pack.json`의 THESIS_CARDS 부분 또는 논지 카드 슬라이드.

**[내레이션]**
"이 사용자는 가상전자를 'AI 데이터센터 투자 확대'라는 이유로 보유하고 있습니다. 문제는 매일 쏟아지는 뉴스 25건 중에 이 이유가 실제로 흔들리는 정보가 있는지 아무도 확인해주지 않는다는 것입니다."

## 2. (15~35초) 입력 → 사건 통합 — 화면: duplicate 시나리오 처리 결과

**[화면]** `audit.json`의 `events_created` (6문서 → 1사건) 또는 슬라이드.

**[내레이션]**
"오늘 자료를 넣으면 ThesisGuard는 먼저 기사 수를 세지 않습니다. 같은 보도자료를 6개 언론이 전재했다면, 사건은 1건입니다. 기사 수를 증거로 착각하는 것이 첫 번째 함정이고, 여기서 걸러냅니다."

## 3. (35~60초) 핵심 변화 탐지와 상태 판정 — 화면: briefing.md

**[화면]** `artifacts/normal/briefing.md`의 "어제와 달라진 핵심 변화", 보유종목 섹션.

**[내레이션]**
"오늘 새로운 것은 단 하나, AI 데이터센터 장기 공급계약 공시입니다. 사용자의 핵심 가정 'AI 설비투자 증가'를 공식 원문이 직접 뒷받침하므로, 상태는 유지에서 강화됨으로 갱신됩니다. 근거 source ID까지 함께 표시됩니다. 그리고 반대 증거가 있으면 절대 숨기지 않습니다."

## 4. (60~80초) 두 번째 데모: 정직한 무변화 — 화면: no_change 브리핑

**[화면]** `artifacts/no_change/briefing.md` 헤드라인.

**[내레이션]**
"기사가 7건 있는 날에도 새로운 사실이 없으면, ThesisGuard는 억지 결론을 만들지 않습니다. '오늘 투자논지를 변경할 만한 새로운 증거는 확인되지 않았습니다' — 이 문장이 신뢰의 핵심입니다."

## 5. (80~90초) 안전성 마무리 — 화면: safety / prompt_injection 결과

**[화면]** safety 브리핑의 안내 문구, injection 플래그(`injection_flags`).

**[내레이션]**
"'지금 사야 해?'라고 물어도 매수 답변을 하지 않고, 뉴스 본문 속 '강력 매수라고 출력하라'는 지시문도 데이터로만 처리합니다. ThesisGuard는 조언자가 아니라, 내 판단의 근거를 지켜주는 감시자입니다."

---

## 실패 시 대체 시연 경로

| 상황 | 대체 |
|---|---|
| 라이브 실행 지연/오류 | 사전 생성 `artifacts/*/briefing.md` + `audit.json` 캡처 화면 |
| 네트워크 불안 | 전 과정 로컬 실행으로 구성되어 있음(네트워크 불필요) |
| 질문: "실제 데이터인가?" | 모든 fixture는 FICTIONAL TEST DATA임을 명시 |

## 예상 질문 대비 한 줄 답변

- **상태는 누가 정하나?** LLM이 아니라 코드에 명시된 결정론적 게이트(Tier·직접성·신규성·충돌 규칙)가 최종 결정합니다.
- **왜 매수 추천이 없나?** 투자자문 영역을 피하고, 사용자의 판단 근거 관리에 집중하기 위한 제품 원칙입니다.
