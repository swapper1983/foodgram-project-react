FROM python

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

COPY requirements.txt ./

RUN apt-get update && apt-get upgrade -y
RUN pip install -r requirements.txt --no-cache-dir

COPY . .
COPY ./entrypoint.sh /
ENTRYPOINT ["sh", "/entrypoint.sh"]