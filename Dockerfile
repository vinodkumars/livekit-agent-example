# Single stage build
FROM python:3.11-slim

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Install gcc and other build dependencies.
RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Install Python dependencies (locked)
WORKDIR /agent
COPY ./uv.lock ./pyproject.toml ./
RUN uv sync --no-dev --frozen --no-cache

COPY . .
ENV PATH="/agent/.venv/bin:$PATH"

# ensure that any dependent models are downloaded at build-time
RUN python app/agent.py download-files

# expose healthcheck port
EXPOSE 8081

# Run the application.
CMD ["python", "app/agent.py", "start"]