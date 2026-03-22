FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# uv 설치
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# 👉 수정된 부분: PATH 경로 변경
ENV PATH="/root/.local/bin:${PATH}"

# 프로젝트 파일 복사
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY backend/ ./backend/

# 데이터베이스 디렉토리 생성
RUN mkdir -p /app/data

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]