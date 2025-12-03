# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream9-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream9

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y podman python3.12 git redis wget postfix

RUN printf "#!/bin/bash\npostfix start\nexec \"\$@\"" > run.sh
RUN chmod 777 run.sh

ENTRYPOINT ["/run.sh"]
CMD ["cat"]
