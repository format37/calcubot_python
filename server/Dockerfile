FROM python:3.14.0-slim-trixie
WORKDIR /server
COPY requirements.txt /server

# Install build dependencies for scipy, matplotlib, and pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    && pip3 install -r requirements.txt --no-cache-dir \
    && apt-get purge -y --auto-remove build-essential gfortran \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the timezone.
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create sandbox directory for isolated eval execution
RUN mkdir -p /server/sandbox

# Copy main server files (config.json mounted at runtime stays here)
COPY server.py /server
COPY blocked_users.txt /server
COPY unsecure_words.txt /server

# Copy eval scripts to sandbox (isolated from config.json and secrets)
COPY sandbox/calculate_inline.py /server/sandbox/
COPY sandbox/calculate_native.py /server/sandbox/
COPY sandbox/user_defined.py /server/sandbox/
# COPY bot_config.json /server
# CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "15", "server:app"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
# CMD ["python", "server.py"]