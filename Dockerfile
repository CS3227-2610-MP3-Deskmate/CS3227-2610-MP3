# Deskmate's app image (SECURITY-SPEC "Container image"). Nothing serves from
# it yet: its default command checks the project and exits.

# Official Python image, pinned to its version and its multi-platform digest.
# Debian trixie, the same release as compose.yaml's PostgreSQL image.
FROM python:3.14.2-slim-trixie@sha256:1a3c6dbfd2173971abba880c3cc2ec4643690901f6ad6742d0827bae6cefc925

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# The app runs as this system user, which has no home, password or login shell.
RUN groupadd --system deskmate \
    && useradd --system --gid deskmate --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin deskmate

WORKDIR /app

# Runtime dependencies only; the test and lint tools stay out of the image.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --requirement /tmp/requirements.txt && rm /tmp/requirements.txt

# The code stays owned by root, so the app cannot change it. .dockerignore
# leaves out the tests and caches.
COPY src/ /app/

USER deskmate

# No configuration is baked in: the variables in TECHNICAL-SPEC "Configuration"
# are given when the container runs, and the check fails without them (PLT-1.7).
CMD ["python", "manage.py", "check"]
