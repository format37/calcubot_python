FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir

# Set the timezone.
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY calculate_inline.py /server
COPY calculate_native.py /server
COPY user_defined.py /server
COPY server.py /server
COPY blocked_users.txt /server
COPY unsecure_words.txt /server
# COPY bot_config.json /server
# CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "15", "server:app"]
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
# CMD ["python", "server.py"]