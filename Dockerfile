# Read the doc: https://huggingface.co/docs/hub/spaces-sdks-docker
# you will also find guides on how best to write your Dockerfile

FROM python:3.12

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Fix: Copy files to /app instead of /main to match WORKDIR
COPY --chown=user . /app

# Make sure models directory exists
RUN mkdir -p /app/models

# Run the app using port 7860 (standard for HF Spaces)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
