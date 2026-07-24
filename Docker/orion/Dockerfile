# Based on cloud-bulldozer/orion's own Dockerfile, with fixes found while validating
# this integration:
#   - python-311 instead of python-314: orion pins scikit-learn==1.5.0, which has no
#     prebuilt wheel for cp314 and fails to build from source in this base image.
#   - no forced --no-binary build of cryptography: the source build fails via cargo/maturin;
#     the prebuilt wheel works fine for our use.
#   - single stage instead of multi-stage: the final stage's COPY --from=builder breaks on
#     Fedora's /opt/app-root/lib64 -> lib symlink, since the builder's manual site-packages
#     extraction step turns it into a real directory instead of preserving the symlink.
FROM quay.io/fedora/python-311:latest

USER 0

RUN dnf install -y \
    git \
    gcc \
    make \
    rust \
    cargo \
    openssl-devel \
    python3-devel \
    pkg-config \
    && dnf clean all

WORKDIR /build

# Pinned to a specific commit for reproducible builds.
ARG ORION_COMMIT=b0acf1948e017164a45ca0af309b69d05ed4735a
RUN git clone https://github.com/cloud-bulldozer/orion.git . && \
    git checkout "${ORION_COMMIT}"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

ENV PYTHONUNBUFFERED="1"

# orion writes its output (CSV/report files) to the current working directory;
# /tmp is writable by any UID, unlike /build which is root-owned from the build above.
WORKDIR /tmp

USER 1001

ENTRYPOINT ["orion"]
