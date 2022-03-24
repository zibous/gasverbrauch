#!/bin/bash

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

echo("Copy service template")
cp /opt/gasverbrauch/service.template  /etc/systemd/system/gasverbrauch.service

echo("Reload service deamon")
systemctl daemon-reload

echo("Start and enable service")
systemctl start gasverbrauch.service
systemctl enable gasverbrauch.service

echo("Status service gasverbrauch")
systemctl status gasverbrauch.service
