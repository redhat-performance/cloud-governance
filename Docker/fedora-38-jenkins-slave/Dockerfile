
# This image for Jenkins slave
# located: quay.io/cloud-governance/fedora38-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/fedora/fedora:38

RUN dnf update -y &&  dnf install -y podman python3.14 git redis wget postfix
RUN printf "#!/bin/bash\npostfix start\ncat" > run.sh
RUN chmod 777 run.sh

ENTRYPOINT ["/run.sh"]
