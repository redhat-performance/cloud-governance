FROM python:3.8-slim

RUN python -m pip install --upgrade pip && pip install cloud-governance
RUN pip3 --no-cache-dir install --upgrade awscli
ADD cloud_governance/policies /usr/local/cloud_governance/policies/
COPY cloud_governance/main/run.py /usr/local/cloud_governance/run.py

CMD [ "python", "/usr/local/cloud_governance/run.py"]
