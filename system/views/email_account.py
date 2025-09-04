#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin-server
# filename : email_account
# author : ly_13
# date : 8/12/2024

from django_filters import rest_framework as filters

from common.core.filter import BaseFilterSet
from common.core.modelset import BaseModelSet
from system.models import UserEmailAccount
from system.serializers.email_account import UserEmailAccountSerializer


class UserEmailAccountFilter(BaseFilterSet):
    pk = filters.UUIDFilter(field_name='id')

    class Meta:
        model = UserEmailAccount
        fields = ['pk', 'user', 'protocol', 'is_active']


class UserEmailAccountViewSet(BaseModelSet):
    """用户邮箱账号"""
    queryset = UserEmailAccount.objects.all()
    serializer_class = UserEmailAccountSerializer
    ordering_fields = ['created_time']
    filterset_class = UserEmailAccountFilter
