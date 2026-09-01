FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock ./requirements.lock

# Install the locked runtime dependency set before copying application code so
# source edits do not invalidate the dependency layer. Remove pip, setuptools,
# and wheel afterward because build tooling is unnecessary at runtime and its
# vendored libraries inflate the image's vulnerability surface.
RUN pip install --upgrade pip "setuptools>=78.1.1" wheel && \
    pip install --require-hashes -r requirements.lock && \
    pip check && \
    rm -f requirements.lock && \
    pip uninstall -y pip setuptools wheel

COPY alembic.ini /app/alembic.ini
COPY app /app/app
COPY alembic /app/alembic
COPY scripts /app/scripts
COPY start_with_migrations.sh /app/start.sh

RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
