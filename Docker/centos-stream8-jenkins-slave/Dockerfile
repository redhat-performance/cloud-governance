# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream8-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream8

RUN dnf update -y &&  dnf install -y podman python3.9 git redis wget postfix
RUN printf "#!/bin/bash\npostfix start\ncat" > run.sh
RUN chmod 777 run.sh

ENTRYPOINT ["/run.sh"]
