# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream9-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream9

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y podman python3.12 git redis wget postfix

# Create run.sh - simplified, always exec
RUN cat > /run.sh << 'EOF'
#!/bin/bash
# Start postfix only if main.cf exists as a file (not directory)
[ -f /etc/postfix/main.cf ] && postfix start >/dev/null 2>&1 || true
# Always execute Jenkins' command (cat)
exec "$@"
EOF
RUN chmod +x /run.sh

ENTRYPOINT ["/run.sh"]
CMD ["cat"]
