#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : email_account
# author : ly_13
# date : 8/12/2024

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.base.utils import signer
from common.core.models import DbAuditModel, DbUuidModel


class UserEmailAccount(DbAuditModel, DbUuidModel):
    class ProtocolChoices(models.TextChoices):
        IMAP = 'IMAP', _("IMAP")
        POP3 = 'POP3', _("POP3")
        SMTP = 'SMTP', _("SMTP")

    user = models.ForeignKey("system.UserInfo", on_delete=models.CASCADE, related_name="email_accounts",
                             verbose_name=_("User"))
    host = models.CharField(max_length=255, verbose_name=_("Host"))
    port = models.PositiveIntegerField(verbose_name=_("Port"))
    protocol = models.CharField(max_length=10, choices=ProtocolChoices.choices, verbose_name=_("Protocol"))
    username = models.CharField(max_length=255, verbose_name=_("Username"))
    _password = models.CharField(db_column="password", max_length=255, verbose_name=_("Password"))
    use_ssl = models.BooleanField(default=True, verbose_name=_("Use SSL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    @property
    def password(self):
        try:
            return signer.decrypt(self._password)
        except Exception:
            return ""

    @password.setter
    def password(self, value: str):
        if value:
            self._password = signer.encrypt(value.encode("utf-8")).decode("utf-8")
        else:
            self._password = ""

    class Meta:
        verbose_name = _("User email account")
        verbose_name_plural = verbose_name
        ordering = ("-created_time",)

    def __str__(self):
        return f"{self.username}@{self.host}"
