# English Crew 릴리스 저장소 (English Crew Releases)

고등학교 영어 교사를 위한 2022 개정 교육과정 기반 수업·평가 설계 및 분석적 루브릭 생성 데스크톱 애플리케이션의 공식 다운로드 저장소입니다.

---

## 1. 앱 소개
- **교육과정 성취기준 100% 무결 인용**: 2022 개정 교육과정 영어과 공식 문서의 성취기준 원문만을 조회하여 인용하며 허위 성취기준 생성을 원천 차단합니다.
- **분석적 루브릭 자동 검증**: 모호한 형용사적 평가 대신 관찰 및 측정이 가능한 객관적 행동 지표를 바탕으로 4수준 루브릭을 완성합니다.
- **교사 결재 중심 워크플로**: 모든 산출물은 교사의 최종 검토와 결재 승인을 거쳐 공문 규격 서식의 한글/워드(.docx) 파일로 안전하게 내보내집니다.

---

## 2. 최신 버전 다운로드 (v1.0.0)

| 배포 형태 | 다운로드 링크 | 파일명 | 권장 대상 |
|---|---|---|---|
| **설치형 (NSIS)** | [다운로드 (Setup)](https://github.com/googyosoo/english-crew-releases/releases/latest/download/EnglishCrew-Setup.exe) | `EnglishCrew-Setup.exe` | 시작 메뉴 및 바탕화면 바로가기 등록 희망 교사 |
| **무설치형 (포터블)** | [다운로드 (Portable)](https://github.com/googyosoo/english-crew-releases/releases/latest/download/EnglishCrew-Portable.exe) | `EnglishCrew-Portable.exe` | USB 또는 임의 폴더에서 즉시 실행 희망 교사 |

> **무결성 검증 (SHA-256 Checksum)**:
> 다운로드 파일의 무결성은 함께 배포되는 [SHA256SUMS.txt](https://github.com/googyosoo/english-crew-releases/releases/latest/download/SHA256SUMS.txt) 파일을 통해 확인할 수 있습니다.

---

## 3. 시스템 요구 사항
- **운영체제**: Microsoft Windows 10 / 11 (64-bit)
- **네트워크**: Google Gemini API 통신을 위한 인터넷 연결 필요
- **준비물**: 개인 Google Gemini API 키 (앱 첫 실행 시 설정 창에서 입력)

---

## 4. Windows SmartScreen 안내
설치 또는 실행 시 **"Windows의 PC 보호"** 알림 창이 나타날 수 있습니다.
이는 오픈소스 소프트웨어 배포 초기 유료 코드 서명 인증서가 미적용되어 발생하는 Windows Defender 기본 동작입니다.
1. 화면의 **[추가 정보]** 링크를 클릭합니다.
2. 하단에 나타나는 **[실행]** 버튼을 클릭하여 정상적으로 시작합니다.

---

## 5. 학생 개인정보 및 보안 보호 원칙
- **로컬 격리 저장**: 학생 명단, 세부 기록, 교사의 Gemini API 키는 교사의 로컬 PC(보안 사용자 데이터 디렉터리)에만 보관되며 외부 서버로 전송되지 않습니다.
- **실명 가명화 처리**: Gemini API와 통신할 때 학생 실명은 `Student 1`, `Student 2` 등의 난수화된 가명으로 치환 전송되며, 교사 화면 수신 시 로컬 메모리에서 복원됩니다.
- **오프라인 검증 체계**: 교육과정 원문 데이터베이스와 루브릭 검사 엔진은 로컬 바이너리 내부에서 완전히 오프라인으로 검증을 수행합니다.
