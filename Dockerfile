FROM ubuntu:24.04

RUN apt-get update && apt-get install -y wget unzip && rm -rf /var/lib/apt/lists/*

ARG GODOT_VERSION=4.5-stable

COPY scripts/install_godot.sh ./install_godot.sh
COPY scripts/install_godot_export_templates.sh ./install_godot_export_templates.sh

RUN chmod +x install_godot.sh install_godot_export_templates.sh && \
    ./install_godot.sh ${GODOT_VERSION} && \
    ./install_godot_export_templates.sh ${GODOT_VERSION}

# Verify export templates installation
RUN echo "Verifying export templates installation..." && \
    ls -la /root/.local/share/godot/export_templates/${GODOT_VERSION}/ || echo "Export templates directory not found"

WORKDIR /workspace

CMD ["godot", "--version"]