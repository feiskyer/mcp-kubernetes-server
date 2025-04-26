# Builder image
FROM python:3.12-bullseye AS builder

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app
COPY . /app

RUN $HOME/.local/bin/uv build

# Final image
FROM python:3.12-bullseye

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
  chmod +x kubectl && mv kubectl /usr/local/bin/kubectl && \
  curl -sSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash && \
  useradd --create-home --shell /bin/bash mcp

COPY --from=builder /app/dist/*.whl /tmp
RUN pip install /tmp/*.whl && rm -f /tmp/*.whl

USER mcp

ENTRYPOINT [ "/usr/local/bin/mcp-kubernetes-server" ]