# 1. Instruct the server to use an official Python environment
FROM python:3.13-slim

# 2. Set the working directory inside the server
WORKDIR /app

# 3. Copy only your backend requirements first
COPY backend/requirements.txt .

# 4. Install the requirements using pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend code into the server
COPY backend/ .

# 6. Start FastAPI using Railway's dynamic PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]