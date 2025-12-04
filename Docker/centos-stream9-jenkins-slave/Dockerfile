# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream9-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream8

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y podman python3.12 python3.12-pip git redis wget postfix
RUN printf "#!/bin/bash\npostfix start\ncat" > run.sh
RUN chmod 777 run.sh

ENTRYPOINT ["/run.sh"]
