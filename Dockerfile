FROM python:3.14-slim-bookworm AS fuente
WORKDIR /src
COPY . .
RUN python deploy/oracle/sanear_imagen.py && rm deploy/oracle/sanear_imagen.py

FROM node:22-bookworm-slim AS frontend
WORKDIR /src
COPY --from=fuente /src/piloto_spa/frontend/ piloto_spa/frontend/
RUN cd piloto_spa/frontend && npm ci --no-audit --no-fund
COPY --from=fuente /src/piloto_spa/backend/static/index.html piloto_spa/backend/static/index.html
RUN cd piloto_spa/frontend && npm run build

FROM python:3.14-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app HOME=/tmp
WORKDIR /app
COPY requirements.txt deploy/oracle/constraints.txt ./
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt -c constraints.txt && pip check \
    && groupadd --gid 10001 usaer && useradd --uid 10001 --gid 10001 --no-create-home usaer
COPY --from=fuente /src/ ./
COPY --from=frontend /src/piloto_spa/frontend/dist/ piloto_spa/frontend/dist/
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["python", "/app/deploy/oracle/arranque.py"]
CMD ["servir"]
