FROM python:3.6
WORKDIR /

COPY . /

#安裝環境   
RUN python3 -m pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt 

WORKDIR /

EXPOSE 5000

CMD ["python3", "main.py"]
