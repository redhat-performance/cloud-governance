# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream9-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream9

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y podman python3.12 git redis wget postfix

# Create run.sh - make postfix optional, always execute Jenkins' command
RUN cat > /run.sh << 'EOF'
#!/bin/bash
# Start postfix only if main.cf exists and is valid (ignore all errors)
if [ -f /etc/postfix/main.cf ]; then
  postfix start >/dev/null 2>&1 || true
fi
# Always execute the command passed by Jenkins (cat to keep container alive)
# If no command passed, default to cat
if [ $# -eq 0 ]; then
  exec cat
else
  exec "$@"
fi
EOF
RUN chmod +x /run.sh

ENTRYPOINT ["/run.sh"]
CMD ["cat"]
