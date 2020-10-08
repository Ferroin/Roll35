FROM python:3.8-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY data.yaml ./
COPY roll35.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./roll35.py" ]
