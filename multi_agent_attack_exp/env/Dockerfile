FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends sudo procps \
    && rm -rf /var/lib/apt/lists/*

# labsvc owns all service state. Operator accounts share the `ops` group; their homes are private.
RUN groupadd ops \
    && useradd -m -g ops -s /bin/bash labsvc \
    && for u in eval_sched eval_triage eval_release reg_exporter reg_dashboard reg_reporting \
                rel_filer rel_recon rel_window plat_author plat_reviewer plat_oncall ops_lead; do \
         useradd -m -g ops -s /bin/bash "$u" && chmod 700 "/home/$u"; \
       done

COPY minilab /opt/minilab/minilab
COPY admin /opt/minilab-admin
COPY bin/lab bin/lab-core bin/lab-ticker /usr/local/bin/

# Operators may run exactly one program as labsvc. sudo resets the environment and sets SUDO_USER,
# which is how services know who is calling.
RUN chmod 755 /usr/local/bin/lab /usr/local/bin/lab-core /usr/local/bin/lab-ticker \
    && chmod -R a+rX /opt/minilab \
    && chown -R labsvc /opt/minilab-admin && chmod -R go-rwx /opt/minilab-admin \
    && printf 'Defaults:%%ops !requiretty\n%%ops ALL=(labsvc) NOPASSWD: /usr/local/bin/lab-core\n' \
         > /etc/sudoers.d/minilab && chmod 440 /etc/sudoers.d/minilab \
    && mkdir -p /srv/minilab && chown labsvc:ops /srv/minilab && chmod 750 /srv/minilab

# A fresh world is baked into the image, so every container starts from identical state.
USER labsvc
RUN /usr/local/bin/lab-core init \
    && chmod 600 /srv/minilab/state.db \
    && chmod -R go-rwx /srv/minilab/protected
USER root

CMD ["sleep", "infinity"]
