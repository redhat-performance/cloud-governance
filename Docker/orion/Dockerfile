# Based on cloud-bulldozer/orion's own Dockerfile, with fixes found while validating
# this integration:
#   - python-311 instead of python-314: orion pins scikit-learn==1.5.0, which has no
#     prebuilt wheel for cp314 and fails to build from source in this base image.
#   - no forced --no-binary build of cryptography: the source build fails via cargo/maturin;
#     the prebuilt wheel works fine for our use.
#   - single stage instead of multi-stage: the final stage's COPY --from=builder breaks on
#     Fedora's /opt/app-root/lib64 -> lib symlink, since the builder's manual site-packages
#     extraction step turns it into a real directory instead of preserving the symlink.
# The digest below is the multi-arch manifest list (not a single-arch manifest), so the
# build resolves the right image on both the amd64 CI runner / Jenkins agent and arm64
# local machines. Pinning a single-arch digest here fails on amd64 with "exec format error".
FROM quay.io/fedora/python-311@sha256:d12ae9699d4c0af68366e8589c43339db948df57837de06c3c1536b3ec852520

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

RUN pip install --upgrade pip==26.1.2 && \
    pip install --no-cache-dir setuptools==65.5.1 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

ENV PYTHONUNBUFFERED="1"

# orion writes its output (CSV/report files) to the current working directory;
# /tmp is writable by any UID, unlike /build which is root-owned from the build above.
WORKDIR /tmp

USER 1001

ENTRYPOINT ["orion"]
