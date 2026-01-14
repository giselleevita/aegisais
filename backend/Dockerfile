FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
RUN pip install -U pip && pip install -e .

COPY app /app/app
COPY alembic /app/alembic

EXPOSE 8000

# Create startup script that runs migrations then starts the server
RUN echo '#!/bin/bash\nset -e\necho "Running database migrations..."\nalembic upgrade head\necho "Starting server..."\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
