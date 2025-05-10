FROM ubuntu:24.04
# 필요한 패키지를 업데이트하고 설치합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
    # uv 설치
    # && curl -LsSf https://astral.sh/uv/install.sh | sh

# UV 설치 및 설치 경로 확인
RUN curl -LsSf https://astral.sh/uv/install.sh -o install_uv.sh && \
    chmod +x install_uv.sh && \
    ./install_uv.sh && \
    rm install_uv.sh

# UV가 설치된 경로를 명시적으로 PATH에 추가 (일반적인 설치 경로는 /root/.local/bin)
ENV PATH="$PATH:/root/.local/bin"

# UV 버전 확인 (설치 확인용 - 빌드 시 에러는 무시해도 됨)
RUN echo "Attempting to check uv version during build..." && uv --version || true
WORKDIR /app

COPY crawler.py .
COPY pyproject.toml .
# ACCESS_TOKEN을 docker build시 명령어에 넣습니다. docker build --build-arg ACCESS_TOKEN=<토큰> -t <이미지 이름>
# ARG ACCESS_TOKEN
# RUN git clone https://${ACCESS_TOKEN}@github.com/KMS-114/real-estate-agent.git
# RUN git clone https://${ACCESS_TOKEN}@github.com/Yanghojun/mcp_crawler.git

# COPY requirements.txt .

# WORKDIR /workspace/mcp_crawler

RUN uv init && uv venv
#  && uv pip install -r requirements.txt

CMD ["uv", "run", "crawler.py"]