FROM ubuntu:24.04

RUN apt-get update && apt-get install -y wget unzip && rm -rf /var/lib/apt/lists/*

ARG GODOT_VERSION=4.6-stable

COPY scripts/install_godot.sh ./install_godot.sh
COPY scripts/install_godot_export_templates.sh ./install_godot_export_templates.sh

RUN chmod +x install_godot.sh install_godot_export_templates.sh && \
    ./install_godot.sh ${GODOT_VERSION} && \
    ./install_godot_export_templates.sh ${GODOT_VERSION}

# Expose the shared templates dir at the per-user path Godot looks for.
# /etc/skel is copied into any future `useradd -m` user's home, and the /root
# symlink keeps the legacy path working for containers that run as root.
RUN mkdir -p /etc/skel/.local/share/godot /root/.local/share/godot && \
    ln -sfn /usr/local/share/godot/export_templates /etc/skel/.local/share/godot/export_templates && \
    ln -sfn /usr/local/share/godot/export_templates /root/.local/share/godot/export_templates

WORKDIR /workspace

CMD ["godot", "--version"]