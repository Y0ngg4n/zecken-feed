FROM	docker.io/library/python

ENV	PYTHONUNBUFFERED	1
WORKDIR	/app
RUN	apt-get update \
	&& apt-get upgrade -y
ADD	./requirements.txt	/app/requirements.txt
RUN	python3 -m pip install --no-cache-dir --upgrade -r requirements.txt
ADD	./*.py	/app
CMD	["fastapi","run","main.py","--port","8000"]
