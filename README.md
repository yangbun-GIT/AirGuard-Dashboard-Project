# 🍃 AirGuard Dashboard Project (스마트 환기 및 야외 운동 알리미)

`Streamlit + FastAPI + SQLite` 기반으로 구축된 기상 및 대기 상태 종합 분석 대시보드입니다.

## 🎯 Project Purpose
공공데이터포털의 OpenAPI를 활용하여 사용자가 거주하는 지역의 **날씨(기온, 강수)와 대기오염(미세먼지, 자외선) 데이터를 종합적으로 분석**합니다. 단순히 수치를 나열하는 것을 넘어, **"지금 환기를 해도 좋은지?", "지금 야외 운동을 하기에 적합한지?"**를 0~100점의 직관적인 점수와 지도로 안내하는 것을 목적으로 합니다.

---

## ✨ Main Features
- **전국 지역 계층형 검색**
- **실시간 지수 산출 알고리즘**
- **반응형 지도 시각화**
- **데이터 캐싱 & Fallback**
- **Glassmorphism UI**

---

## 🛠 Tech Stack & Libraries

### Frontend (UI/UX & Visualization)
- **[Streamlit]**: 전체 웹 대시보드 프레임워크 및 라우팅
- **[Folium] / [streamlit-folium]**: 동적 지도 생성 및 마커/팝업 시각화
- **[Pandas]**: 드롭다운 UI 구성을 위한 지역 데이터 계층화 및 필터링

### Backend (API, Logic & Data Processing)
- **[FastAPI] / [Uvicorn]**: 비동기 RESTful API 서버 구축 및 프론트엔드 라우팅
- **[httpx]**: 공공데이터 OpenAPI 비동기 통신 (`asyncio` 병렬 처리)
- **[pyproj]**: WGS84(위경도) ↔ TM/격자 좌표계 실시간 변환
- **[openpyxl]**: `region_data.xlsx` 원본 파일 데이터 파싱

### Database & Infra
- **[SQLite3] / [SQLAlchemy] / [aiosqlite]**: 비동기 RDBMS 세션 관리 및 캐시/지역 데이터 저장
- **[uv]**: 초고속 Python 패키지 및 가상환경 관리 매니저
- **[Docker] / [Docker Compose]**: 프론트엔드와 백엔드의 독립된 컨테이너화 및 오케스트레이션

---

## 🔗 Used Public APIs

본 프로젝트는 공공데이터포털(https://www.data.go.kr/index.do)의 데이터를 활용합니다.

1. **[한국환경공단_에어코리아_측정소정보](https://www.data.go.kr/data/15073877/openapi.do)**
   - **역할**: 사용자 좌표(TM 변환)를 기반으로 가장 가까운 대기질 측정소 탐색
2. **[한국환경공단_에어코리아_대기오염정보](https://www.data.go.kr/data/15073861/openapi.do)**
   - **역할**: 탐색된 측정소의 실시간 미세먼지(PM10, PM2.5) 수치 조회
3. **[기상청_단기예보 ((구)_동네예보) 조회서비스 (초단기실황)](https://www.data.go.kr/data/15084084/openapi.do)**
   - **역할**: 격자 좌표계를 기반으로 현재 기온 및 강수 형태(비/눈) 실시간 조회
4. **[기상청_생활기상지수 조회서비스(3.0)](https://www.data.go.kr/data/15085288/openapi.do)**
   - **역할**: 지역 기반 현재 자외선 지수 조회
> *참고: 행정구역 코드는 API 호출 대신 기상청에서 제공하는 [행정동 및 도로명주소 변경사항 현행화 자료]를 로컬(`region_data.xlsx`)에서 직접 파싱하여 사용합니다.*

---

## 🚀 Quick Start (초보자용 실행 가이드)

### 0. 사전 준비사항
- Python 3.11 이상 설치
- 공공데이터포털 회원가입 및 API 사용 신청 (일반 인증키 - Decoding 필요)
- 프로젝트 최상위 폴더에 `.env` 파일을 생성하고 아래와 같이 키를 입력합니다.
  ```env
  SERVICE_KEY=본인의_디코딩된_공공데이터포털_API_키를_입력하세요
  ```
- 기상청 엑셀 데이터 파일(`region_data.xlsx`)이 반드시 `backend/` 폴더 안에 위치해야 합니다.

### 방법 1. Docker를 이용한 실행 (권장)
가장 쉽고 확실한 방법입니다. 로컬 컴퓨터에 Docker Desktop이 실행 중이어야 합니다.

```bash
# 백엔드와 프론트엔드 컨테이너를 동시에 빌드하고 실행합니다.
docker-compose up --build
```
- **Frontend 대시보드**: http://localhost:8501
- **Backend API 문서**: http://localhost:8000/docs

### 방법 2. 로컬 환경에서 직접 실행 (`uv` 패키지 매니저 활용)
도커 없이 직접 코드를 수정하며 테스트하고 싶을 때 사용합니다.

```bash
# 1. uv 설치 (Windows PowerShell 기준)
irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex

# 2. 필수 라이브러리 한번에 설치
uv add fastapi uvicorn httpx sqlalchemy aiosqlite pandas streamlit folium streamlit-folium python-dotenv pyproj openpyxl

# 3. 백엔드 서버 실행 (터미널 창 1)
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 프론트엔드 서버 실행 (터미널 창 2 열기)
uv run streamlit run frontend/app.py
```

---

## 📂 Project Structure

```text
AirGuard-Dashboard-Project/
├── .env                        # 공공데이터 API 키 보관 (Git 제외)
├── .gitignore                  # Git 업로드 제외 목록
├── .dockerignore               # Docker 빌드 제외 목록
├── docker-compose.yml          # 컨테이너 오케스트레이션 설정
├── pyproject.toml              # uv 패키지 종속성 관리 파일
├── README.md                   # 프로젝트 명세서
├── backend/
│   ├── region_data.xlsx        # 전국 지역 및 좌표 매핑 원본 엑셀
│   ├── api_client.py           # 외부 공공데이터 API 비동기 호출 모듈
│   ├── database.py             # SQLite 스키마 및 DB 세션 관리
│   ├── main.py                 # FastAPI 실행 및 엔드포인트 라우팅
│   ├── service.py              # 지수 산출 비즈니스 로직
│   ├── Dockerfile              # 백엔드 컨테이너 빌드 설정
│   └── data/                   # SQLite DB 파일 저장 폴더 (자동 생성)
└── frontend/
    ├── app.py                  # Streamlit 메인 실행 파일
    ├── components/
    │   ├── map.py              # Folium 지도 렌더링 모듈
    │   └── ui.py               # 지표 카드 및 CSS 스타일링 모듈
    └── Dockerfile              # 프론트엔드 컨테이너 빌드 설정