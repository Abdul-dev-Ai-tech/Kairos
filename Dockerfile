FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock /app/
RUN pip install --no-cache-dir -r requirements.lock
RUN groupadd --gid 10001 kairos && useradd --uid 10001 --gid 10001 --create-home kairos
COPY . /app/
RUN mkdir -p /app/media /app/staticfiles && chown -R kairos:kairos /app/media /app/staticfiles
USER kairos
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
