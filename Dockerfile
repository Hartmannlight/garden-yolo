FROM ultralytics/ultralytics:latest

# Install curl (needed for Poetry installer)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry (pinned to 1.6.1) and update PATH
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.6.1
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Install only runtime deps via Poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-dev --no-interaction

# Copy rest of code
COPY . .

# Ensure image folders exist
RUN mkdir -p /opt/webcam/images /opt/webcam

CMD ["python", "src/monitor.py"]
