FROM public.ecr.aws/docker/library/python:3.10

# Ensure unbuffered output
ENV PYTHONUNBUFFERED=1

# Create app directory and set workdir
WORKDIR /app

# Create and activate virtual environment
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Copy only requirements file to leverage Docker cache
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app
COPY ./scripts /app/scripts
COPY alembic.ini /app/

# Precompile Python bytecode (optional)
RUN python3 -m compileall -q /app/app

# Expose default FastAPI port
EXPOSE 8000

# Launch with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--workers", "4"]

