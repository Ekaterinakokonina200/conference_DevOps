# Инструменты проверки инфраструктурного кода (ЛР №7): make infra-check.
# Образ собирается локально и в CI из закреплённого базового образа и
# requirements-infra.txt, поэтому версии Ansible, ansible-lint и yamllint
# везде одинаковы.
FROM python:3.12.15-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    ANSIBLE_LOCAL_TEMP=/tmp/ansible-local \
    ANSIBLE_HOME=/tmp/ansible

COPY requirements-infra.txt /tmp/requirements-infra.txt
RUN pip install -r /tmp/requirements-infra.txt

USER 10001:10001
WORKDIR /src
