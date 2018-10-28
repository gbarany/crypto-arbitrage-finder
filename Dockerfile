FROM python:3.6.6

# Open port for Visual Studio Code remote python debugger
EXPOSE 5678

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/results
RUN mkdir -p /app/src
RUN mkdir -p /app/cred
COPY src/ ./src
COPY cred/aws-keys.json ./src

RUN mkdir -p ~/.config/matplotlib
RUN echo 'backend : Agg' > ~/.config/matplotlib/matplotlibrc

COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
