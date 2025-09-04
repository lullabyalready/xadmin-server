from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from unittest.mock import patch, MagicMock

from system.models import UserInfo, UserEmailAccount
from system.views.email_account import UserEmailAccountViewSet
from system.tasks_email import fetch_user_emails


class BaseEmailTest(TestCase):
    def setUp(self):
        super().setUp()
        patcher = patch("system.signal_handler.batch_invalid_cache")
        patcher.start()
        self.addCleanup(patcher.stop)


class UserEmailAccountModelTest(BaseEmailTest):
    def test_password_encryption(self):
        user = UserInfo.objects.create_user(username="u", password="p")
        account = UserEmailAccount.objects.create(
            user=user,
            host="imap.example.com",
            port=993,
            protocol=UserEmailAccount.ProtocolChoices.IMAP,
            username="u@example.com",
            password="secret",
        )
        self.assertNotEqual(account._password, "secret")
        self.assertEqual(account.password, "secret")


class UserEmailAccountAPITest(BaseEmailTest):
    def setUp(self):
        super().setUp()
        self.user = UserInfo.objects.create_superuser(
            username="admin", password="admin", email="a@example.com"
        )
        self.factory = APIRequestFactory()

    @patch("system.serializers.email_account.imaplib.IMAP4_SSL")
    def test_create_account(self, mock_imap):
        mock_imap.return_value = MagicMock()
        payload = {
            "user": str(self.user.id),
            "host": "imap.example.com",
            "port": 993,
            "protocol": UserEmailAccount.ProtocolChoices.IMAP,
            "username": "u@example.com",
            "password": "secret",
        }
        request = self.factory.post("/api/system/email/account/", payload, format="json")
        force_authenticate(request, user=self.user)
        response = UserEmailAccountViewSet.as_view({"post": "create"})(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserEmailAccount.objects.count(), 1)


class FetchEmailsTaskTest(BaseEmailTest):
    def setUp(self):
        super().setUp()
        user = UserInfo.objects.create_user(username="user", password="pass")
        self.account = UserEmailAccount.objects.create(
            user=user,
            host="imap.example.com",
            port=993,
            protocol=UserEmailAccount.ProtocolChoices.IMAP,
            username="u@example.com",
            password="secret",
        )

    @patch("system.tasks_email.SiteMessageUtil.send_msg")
    @patch("system.tasks_email.imaplib.IMAP4_SSL")
    def test_fetch_emails(self, mock_imap, mock_send_msg):
        class FakeIMAP:
            def __init__(self, *args, **kwargs):
                pass

            def login(self, *args, **kwargs):
                pass

            def select(self, mailbox):
                pass

            def search(self, charset, criteria):
                return "OK", [b"1"]

            def fetch(self, num, spec):
                msg = b"From: <a@example.com>\nSubject: hi\n\nbody"
                return "OK", [(b"1 (UID 1)", msg)]

            def logout(self):
                pass

        mock_imap.return_value = FakeIMAP()
        fetch_user_emails()
        mock_send_msg.assert_called_once()
