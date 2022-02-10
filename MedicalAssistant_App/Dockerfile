FROM python:3.6
WORKDIR /

COPY . /

#安裝環境   
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
pip install --no-cache-dir -r requirements.txt && \
pip install --upgrade google-api-python-client && \
pip install google.cloud.storage

EXPOSE 5000

CMD ["python3", "main.py"]


