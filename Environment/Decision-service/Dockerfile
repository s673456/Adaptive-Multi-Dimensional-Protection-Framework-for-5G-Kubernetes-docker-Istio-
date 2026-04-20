FROM python:3.9-slim
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY decision_service.py .
CMD ["python", "decision_service.py"]