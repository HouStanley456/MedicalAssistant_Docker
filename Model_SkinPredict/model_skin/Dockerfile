# Pull base image
#FROM python:3.6.15-slim-bullseye
FROM python:3.6

WORKDIR /

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install torch==1.10.1+cpu  torchvision==0.11.2+cpu  torchaudio==0.10.1+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install flask requests pillow==8.4.0 tqdm

# download model
RUN apt update && apt install -qqy wget && wget https://storage.googleapis.com/tfi101linebot/densenetSkin.pt

COPY . /model_skin

COPY app.py /
COPY skinpredict.py /


#EXPOSE 5000
CMD python3 app.py
