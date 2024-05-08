FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_ROOT_USER_ACTION=ignore \
    POETRY_HOME=/root/.poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_VIRTUALENVS_CREATE=false
ENV PATH="/root/.local/bin:$POETRY_HOME/bin:$PATH"

WORKDIR /root

RUN python -m pip install --upgrade pipx \
 && pipx --global ensurepath --force \
 && pipx install poetry

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev

COPY . ./

CMD ["python", "-m", "docker_resolver.main"]
