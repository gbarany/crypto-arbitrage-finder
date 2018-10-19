FROM python:3

EXPOSE 3000
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/results
RUN mkdir -p /app/src
RUN mkdir -p /app/cred
COPY src/ ./src

RUN mkdir -p ~/.config/matplotlib
RUN echo 'backend : Agg' > ~/.config/matplotlib/matplotlibrc

COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
