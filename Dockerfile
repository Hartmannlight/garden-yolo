FROM python:3.12

# Install system dependencies (including libGL for OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry (pinned to version 1.6.1) and update PATH
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.6.1
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction

COPY . .

RUN mkdir -p /opt/webcam/images /opt/webcam

CMD ["python", "src/monitor.py"]
