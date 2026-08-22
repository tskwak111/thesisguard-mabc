# ThesisGuard Codex 구현 시작 안내

## 포함 파일

- `docs/product/2026-08-23-thesisguard-aaa-product-design.md`
  - 제품·에이전트 설계의 단일 기준 문서
- `docs/instructions/2026-08-23-thesisguard-implementation-meta-prompt.md`
  - 저장소 진단부터 TDD 구현, 평가, Timely AI 산출물, 공모전 제출 패키지까지 지시하는 실행 메타프롬프트

## 사용 방법

1. 이 패키지의 내용을 구현할 Git 저장소 루트에 복사한다.
2. Codex를 해당 저장소에서 연다.
3. 아래 시작 프롬프트를 그대로 입력한다.

```text
이 저장소에서 ThesisGuard 예선 제출 가능 버전을 구현해줘.

먼저 다음 두 파일을 처음부터 끝까지 읽고, 두 문서를 이번 작업의 기준으로 사용해.

1. docs/product/2026-08-23-thesisguard-aaa-product-design.md
2. docs/instructions/2026-08-23-thesisguard-implementation-meta-prompt.md

두 번째 파일의 작업 순서, 범위, TDD, 안전 규칙, 검증 게이트, 최종 보고 형식을 모두 준수해. 저장소와 기존 규칙을 먼저 조사하고, 구현계획과 traceability matrix를 작성한 뒤 격리된 브랜치 또는 worktree에서 구현까지 진행해. 비차단적 애매함은 가장 보수적이고 작은 범위로 결정해 기록하고, 설계가 이미 승인되었으므로 치명적 충돌이 없는 한 추가 확인을 기다리지 말고 예선 제출 패키지까지 완성해.

완료라고 말하기 전에 실제 린트, 타입 검사, 테스트, CLI smoke test, 골든 시나리오, 안전·프롬프트 인젝션 검증을 실행하고 결과를 증거와 함께 보고해. 테스트를 실행하지 않았거나 실패한 상태에서는 완료라고 주장하지 마.
```
