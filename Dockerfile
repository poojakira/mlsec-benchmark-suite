FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY mlsec_benchmark_suite ./mlsec_benchmark_suite
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && python -m pip install --no-cache-dir cryptography

RUN useradd --create-home --uid 10001 benchmark
USER benchmark
WORKDIR /evidence

ENTRYPOINT ["mlsec-benchmark"]
