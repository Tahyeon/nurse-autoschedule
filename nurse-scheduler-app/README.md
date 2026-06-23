# 간호사 근무표 자동 생성기

아임웹에 붙여넣던 단일 HTML 코드를 독립 실행 가능한 웹앱 형태로 분리한 프로젝트입니다.

## 파일 구조

```text
nurse-scheduler-app/
├─ index.html
├─ styles.css
├─ app.js
├─ manifest.json
└─ service-worker.js
```

## 실행 방법

파일만 확인할 때는 `index.html`을 브라우저로 열 수 있습니다.

PWA 설치와 서비스워커까지 확인하려면 로컬 서버로 실행해야 합니다.

가장 쉬운 방법은 아래 파일을 더블클릭하는 것입니다.

```text
start-server.bat
```

터미널 창이 열려 있는 동안만 서버가 켜져 있습니다.

```powershell
cd "C:\Users\five0\OneDrive\문서\바이브 코딩 프로그램\nurse-scheduler-app"
node dev-server.js
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:5173/index.html
```

## 다음 단계

1. 병동 내부 테스트용 PWA 배포
2. 2~3개월 피드백 반영
3. Capacitor로 Android 앱 포장

## PWA 준비 상태

아래 항목은 준비되어 있습니다.

```text
manifest.json
service-worker.js
icons/icon-192.png
icons/icon-512.png
icons/maskable-512.png
icons/apple-touch-icon.png
icons/favicon.png
```

PWA 설치 테스트는 `file://`가 아니라 HTTPS 배포 주소에서 확인해야 합니다.

추천 배포 후보:

```text
Netlify
Vercel
Cloudflare Pages
GitHub Pages
```
