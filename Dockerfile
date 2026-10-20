FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m -u 1000 ede && mkdir -p /app/data && chown -R ede:ede /app
COPY --chown=ede:ede api.py app.py corpus.py postgres_corpus.py lexicon.py NOTICE.md index.html ./
COPY --chown=ede:ede static ./static
COPY --chown=ede:ede tools ./tools
COPY --chown=ede:ede data/yoruba-lexicon.jsonl ./data/yoruba-lexicon.jsonl
USER ede
# Explicit, pinned recovery of this project's existing Space artifact, not a new licensed dataset.
RUN python tools/bootstrap_data.py
EXPOSE 7860
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
