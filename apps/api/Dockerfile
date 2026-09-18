FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.lock ./requirements.lock

# The rolling slim tag may briefly contain Debian packages with published fixes
# that are not yet installed in the base layer. Apply those fixes in the runtime
# image and remove package metadata before adding application dependencies.
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

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
