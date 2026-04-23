FROM python:3.14-slim

LABEL quay.expires-after=365d

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

# Pre-install IBM packages, then use a constraints file so pip cannot
# downgrade them when resolving cloud-governance's published dependencies.
RUN python -m pip --no-cache-dir install --upgrade pip "setuptools>=58,<82" wheel && \
    pip --no-cache-dir install ibm-cloud-sdk-core==3.24.4 ibm-platform-services==0.75.0 ibm-vpc==0.33.0 ibm-schematics==1.0.1 && \
    printf 'ibm-cloud-sdk-core==3.24.4\nibm-platform-services==0.75.0\nibm-vpc==0.33.0\nibm-schematics==1.0.1\n' > /tmp/constraints.txt && \
    pip --no-cache-dir install cloud-governance --upgrade -c /tmp/constraints.txt && \
    rm /tmp/constraints.txt
RUN pip3 --no-cache-dir install --upgrade awscli
ADD cloud_governance/policy /usr/local/cloud_governance/policy/
COPY cloud_governance/main/main.py /usr/local/cloud_governance/main.py

CMD [ "python", "/usr/local/cloud_governance/main.py"]
