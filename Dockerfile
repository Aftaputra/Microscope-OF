FROM python:3.6

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.0.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

WORKDIR /app

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

COPY . ./

RUN poetry install --no-dev --no-interaction

EXPOSE 5000
CMD ["poetry", "run", "python", "-m", "openflexure_microscope.api.app"]
