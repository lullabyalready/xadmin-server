#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : tasks_email
# author : auto_generated
# date : 2025-02-14

"""Fetch user emails and convert them to site notifications."""

import email
import imaplib
import poplib
from email.header import decode_header, make_header

from celery import shared_task
from django.utils import timezone

from common.celery.decorator import register_as_period_task
from common.utils import get_logger
from notifications.message import SiteMessageUtil
from system.models import UserEmailAccount

logger = get_logger(__name__)


def _parse_message(msg: email.message.Message) -> tuple[str, str]:
    """Return subject and plain text body from an email message."""
    subject = str(make_header(decode_header(msg.get("Subject", ""))))
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                try:
                    body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    body = part.get_payload()
                break
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
        except Exception:
            body = msg.get_payload()
    return subject, body


@shared_task
@register_as_period_task(interval=300, name="system.fetch_user_emails")
def fetch_user_emails():
    """Fetch unread emails for all active user email accounts.

    Depending on the protocol, login via IMAP or POP3, fetch unread messages,
    update sync markers and store them as site notifications.
    """
    accounts = UserEmailAccount.objects.filter(is_active=True)
    for account in accounts:
        try:
            if account.protocol == UserEmailAccount.ProtocolChoices.IMAP:
                client = imaplib.IMAP4_SSL(account.host, account.port) if account.use_ssl else imaplib.IMAP4(account.host, account.port)
                client.login(account.username, account.password)
                client.select("INBOX")
                criteria = "(UNSEEN)"
                if hasattr(account, "last_uid") and account.last_uid:
                    criteria = f"(UID {account.last_uid + 1}:*)"
                typ, data = client.search(None, criteria)
                last_uid = None
                for num in data[0].split():
                    typ, msg_data = client.fetch(num, "(RFC822 UID)")
                    if typ != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject, body = _parse_message(msg)
                    SiteMessageUtil.send_msg(subject, body, user_ids=[account.user_id])
                    # parse UID from response
                    for item in msg_data[0][0].split():
                        if item.startswith(b"UID"):
                            try:
                                last_uid = int(item.split()[1])
                            except Exception:
                                pass
                update_fields = []
                if last_uid is not None and hasattr(account, "last_uid"):
                    account.last_uid = last_uid
                    update_fields.append("last_uid")
                if hasattr(account, "last_sync_time"):
                    account.last_sync_time = timezone.now()
                    update_fields.append("last_sync_time")
                if update_fields:
                    account.save(update_fields=update_fields)
                client.logout()
            elif account.protocol == UserEmailAccount.ProtocolChoices.POP3:
                client = poplib.POP3_SSL(account.host, account.port) if account.use_ssl else poplib.POP3(account.host, account.port)
                client.user(account.username)
                client.pass_(account.password)
                message_count = len(client.list()[1])
                start = getattr(account, "last_uid", 0) or 0
                for i in range(start + 1, message_count + 1):
                    resp, lines, octets = client.retr(i)
                    msg = email.message_from_bytes(b"\n".join(lines))
                    subject, body = _parse_message(msg)
                    SiteMessageUtil.send_msg(subject, body, user_ids=[account.user_id])
                update_fields = []
                if hasattr(account, "last_uid"):
                    account.last_uid = message_count
                    update_fields.append("last_uid")
                if hasattr(account, "last_sync_time"):
                    account.last_sync_time = timezone.now()
                    update_fields.append("last_sync_time")
                if update_fields:
                    account.save(update_fields=update_fields)
                client.quit()
            else:
                logger.warning(f"Unsupported protocol for account {account}")
        except Exception as exc:
            logger.warning(f"Fetch emails for {account} failed: {exc}")
    return True
