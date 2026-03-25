FROM python:3.13-slim

# cloud-governance latest version
ARG VERSION

# install gitleaks
ARG gitleaks_version=7.0.2
RUN apt-get update \
     && apt-get install -y wget build-essential python3-dev libldap2-dev libsasl2-dev vim \
     && export VER=${gitleaks_version}  \
     && wget https://github.com/zricethezav/gitleaks/releases/download/v$VER/gitleaks-linux-amd64 \
     && mv gitleaks-linux-amd64 gitleaks \
     && chmod +x gitleaks \
     && mv gitleaks /usr/local/bin/ \
     && gitleaks --version

# Pin setuptools<82 so pkg_resources is available when building ibm-cloud-sdk-core
RUN python -m pip --no-cache-dir install --upgrade pip "setuptools>=58,<82" wheel && \
    pip --no-cache-dir install --no-build-isolation ibm-cloud-sdk-core==3.18.0 ibm-platform-services==0.27.0 ibm-vpc==0.21.0 ibm-schematics==1.0.1 && \
    pip --no-cache-dir install cloud-governance --upgrade
RUN pip3 --no-cache-dir install --upgrade awscli
ADD cloud_governance/policy /usr/local/cloud_governance/policy/
COPY cloud_governance/main/main.py /usr/local/cloud_governance/main.py

CMD [ "python", "/usr/local/cloud_governance/main.py"]
