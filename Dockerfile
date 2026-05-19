FROM python:3.12-slim

WORKDIR /app

# opencv の依存ライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# uv のインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 依存パッケージのインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache && \
    uv pip install gunicorn

# アプリケーションのコピー
COPY . .

RUN mkdir -p /app/data /app/uploads

EXPOSE 5000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "server:app"]
