FROM python:3.8-slim

RUN python -m pip install --upgrade pip && pip install cloud-governance
RUN pip3 --no-cache-dir install --upgrade awscli
ADD policies /usr/local/
COPY cloud_governance/run.py /usr/local/run.py

CMD [ "python", "/tmp/run.py"]
