FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home aegis && mkdir -p /app/.local && chown -R aegis:aegis /app
USER aegis
EXPOSE 8000
CMD ["python", "run_server.py", "--host", "0.0.0.0"]
