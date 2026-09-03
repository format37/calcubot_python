FROM python:3.14.0-slim-trixie
WORKDIR /server
COPY requirements.txt /server

# Trimmed dependency set (fastapi + uvicorn + pyTelegramBotAPI and their wheels);
# no native builds needed, so no build-essential/gfortran toolchain.
RUN pip3 install -r requirements.txt --no-cache-dir

# Set the timezone.
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create sandbox directory for isolated eval execution
RUN mkdir -p /server/sandbox

# Unprivileged identity the evaluation subprocess is dropped to (server.py sets
# Popen(user=5000)). It has no home and no login shell.
RUN useradd --system --uid 5000 --user-group --home-dir /nonexistent \
    --shell /usr/sbin/nologin sandbox

# Root-only directory the bot token (config.json) is mounted into at runtime, so
# the uid-5000 evaluation subprocess cannot even traverse to it.
RUN mkdir -p /secrets && chmod 700 /secrets

# Copy main server files (config.json mounted at runtime stays here)
COPY server.py /server
COPY blocked_users.txt /server
COPY unsecure_words.txt /server

# Copy eval scripts to sandbox (isolated from config.json and secrets)
COPY sandbox/seccomp_filter.py /server/sandbox/
COPY sandbox/calc_core.py /server/sandbox/
COPY sandbox/calculate_inline.py /server/sandbox/
COPY sandbox/calculate_native.py /server/sandbox/
COPY sandbox/user_defined.py /server/sandbox/
# COPY bot_config.json /server
# CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "15", "server:app"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
# CMD ["python", "server.py"]