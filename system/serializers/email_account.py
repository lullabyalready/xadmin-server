#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : email_account
# author : ly_13
# date : 8/12/2024

import imaplib
import poplib
import smtplib

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.core.serializers import BaseModelSerializer
from system.models import UserEmailAccount


class UserEmailAccountSerializer(BaseModelSerializer):
    password = serializers.CharField(write_only=True, label=_("Password"))

    class Meta:
        model = UserEmailAccount
        fields = ['pk', 'user', 'host', 'port', 'protocol', 'username', 'password', 'use_ssl', 'is_active']
        read_only_fields = ['pk']

    def validate(self, attrs):
        host = attrs.get('host') or getattr(self.instance, 'host', None)
        port = attrs.get('port') or getattr(self.instance, 'port', None)
        protocol = attrs.get('protocol') or getattr(self.instance, 'protocol', None)
        username = attrs.get('username') or getattr(self.instance, 'username', None)
        password = attrs.get('password') or (self.instance.password if self.instance else None)
        use_ssl = attrs.get('use_ssl') if attrs.get('use_ssl') is not None else getattr(self.instance, 'use_ssl', True)

        try:
            if protocol == UserEmailAccount.ProtocolChoices.IMAP:
                client = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
                client.login(username, password)
                client.logout()
            elif protocol == UserEmailAccount.ProtocolChoices.POP3:
                client = poplib.POP3_SSL(host, port) if use_ssl else poplib.POP3(host, port)
                client.user(username)
                client.pass_(password)
                client.quit()
            elif protocol == UserEmailAccount.ProtocolChoices.SMTP:
                client = smtplib.SMTP_SSL(host, port) if use_ssl else smtplib.SMTP(host, port)
                client.login(username, password)
                client.quit()
            else:
                raise serializers.ValidationError({'protocol': _("Unsupported protocol")})
        except Exception as e:
            raise serializers.ValidationError({'credentials': _("Authentication failed: %s") % e})

        return attrs
