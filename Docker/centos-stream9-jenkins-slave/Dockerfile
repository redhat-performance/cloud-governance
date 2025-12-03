# This image for Jenkins slave
# located: quay.io/cloud-governance/centos-stream9-podman:latest
# run the postfix service within the container
# mount /etc/postfix/main.cf file to the container

FROM quay.io/centos/centos:stream9

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y podman python3.12 git redis wget postfix

# Create run.sh - removed set -e to prevent script from exiting
RUN cat > /run.sh << 'EOF'
#!/bin/bash
# Start postfix in background (ignore errors)
postfix start 2>/dev/null || true
# Execute the command passed by Jenkins (cat to keep container alive)
exec "$@"
EOF
RUN chmod +x /run.sh

ENTRYPOINT ["/run.sh"]
CMD ["cat"]
