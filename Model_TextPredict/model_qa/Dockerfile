# Pull base image
#FROM python:3.6.15-slim-bullseye
FROM python:3.6

WORKDIR /

RUN apt update
RUN apt install -qqy wget
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install torch==1.10.1+cpu torchvision==0.11.2+cpu torchaudio==0.10.1+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html
RUN python3 -m pip install flask
RUN python3 -m pip install transformers

# download model
RUN wget -P /model1 https://storage.googleapis.com/tfi101_model/model1/pytorch_model.bin 
RUN wget -P /model1 https://storage.googleapis.com/tfi101_model/model1/data_features.pkl
RUN wget -P /model1 https://storage.googleapis.com/tfi101_model/model1/config.json
#COPY ./model1 /model1

COPY app.py /app.py
COPY textpredict.py /textpredict.py

#EXPOSE 5000
CMD python3 app.py
