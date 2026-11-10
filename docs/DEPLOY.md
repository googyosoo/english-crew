# English Crew 교사용 배포 가이드 (Deployment Guide)

이 문서는 English Crew 데스크톱 프로그램의 최종 설치 파일(.exe)과 공식 배포 웹페이지(Firebase Hosting)를 교사가 직접 배포하기 위한 단계별 실행 절차를 안내합니다.

---

## 1. 사전 준비 (Prerequisites)

1. **GitHub CLI 설치 및 로그인**:
   ```powershell
   # GitHub CLI 로그인 상태 확인 및 대화형 로그인
   gh auth status
   gh auth login
   ```
2. **Firebase CLI 설치 및 로그인** (Firebase Hosting 배포 시 필요):
   ```powershell
   # Firebase CLI 설치 및 로그인
   npm install -g firebase-tools
   firebase login
   ```

---

## 2. 릴리스 실행 파일 빌드 (Build Binaries)

프로덕션 프론트엔드 및 백엔드 바이너리를 빌드하고, 설치형(NSIS)과 포터블 실행 파일을 생성합니다.

```powershell
# 1. 프론트엔드 빌드 및 백엔드 의존성(requirements.lock) 기반 PyInstaller 빌드
npm run build:all

# 2. Windows 설치형(EnglishCrew-Setup.exe) 및 포터블(EnglishCrew-Portable.exe) 패키징
npx electron-builder --win

# 3. SHA-256 체크섬 파일 확인
Get-Content release\SHA256SUMS.txt
```

---

## 3. GitHub Releases 배포 (Deploy GitHub Releases)

`scripts/publish_release.ps1` 스크립트를 사용하여 공개 릴리스 저장소(`english-crew-releases`)를 생성하고, 바이너리 2개와 체크섬 파일을 릴리스로 업로드합니다.

```powershell
# 기본 실행 (기본 계정: googyosoo, 버전: v1.0.0)
powershell -ExecutionPolicy Bypass -File scripts/publish_release.ps1 -Owner "googyosoo" -Repo "english-crew-releases" -Version "v1.0.0"
```

스크립트 수행 내용:
1. GitHub CLI 로그인 상태 확인
2. `$Owner/english-crew-releases` 저장소가 없으면 공개 저장소로 생성하고 `release-repo/README.md`를 push (소스 코드는 포함되지 않음)
3. `gh release create` 명령으로 `EnglishCrew-Setup.exe`, `EnglishCrew-Portable.exe`, `SHA256SUMS.txt` 업로드
4. `https://github.com/$Owner/english-crew-releases/releases/latest/download/...` 링크의 200 HTTP 상태 응답 자동 검증

---

## 4. Firebase Hosting 안내 웹페이지 배포 (Deploy Hosting)

단일 파일로 구성된 한국어 공식 안내 웹페이지(`hosting/index.html`)를 준비하고 Firebase Hosting에 배포합니다.

```powershell
# 1. 다운로드 링크의 GitHub 계정 치환
powershell -ExecutionPolicy Bypass -File scripts/prepare_hosting.ps1 -Owner "googyosoo"

# 2. 로컬 에뮬레이터에서 미리보기 검증 (포트 5000)
firebase emulators:start --only hosting --project demo-englishcrew

# 3. 실제 Firebase Hosting 배포
firebase deploy --only hosting --project <Firebase프로젝트ID>
```

---

## 5. 배포 후 최종 검증 체크리스트

- [ ] GitHub 릴리스 최신 다운로드 링크(`latest/download/EnglishCrew-Setup.exe`) 정상 응답 확인
- [ ] 다운로드한 파일의 SHA-256 해시가 `release/SHA256SUMS.txt` 및 릴리스 노트와 일치하는지 확인
- [ ] 배포된 Hosting 페이지에서 다운로드 버튼 클릭 시 GitHub Releases 최신 파일로 연결되는지 확인
- [ ] Windows SmartScreen 안내 문구가 정상 노출되는지 확인
