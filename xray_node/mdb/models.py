import json
from typing import Any, Union, Type

from tortoise import fields
from tortoise.models import Model


class IPSetField(fields.CharField):
    def to_db_value(self, value: Any, instance: "Union[Type[Model], Model]") -> Any:
        if type(value) is not set:
            value = []
        data = json.dumps(list(value))
        if len(data) > self.max_length:
            raise ValueError("Data too long.")
        return data

    def to_python_value(self, value: Any) -> Any:
        if value is None:
            return value
        _v = json.loads(value)
        return set(_v)


class User(Model):
    id = fields.BigIntField(pk=True)
    email = fields.CharField(description="邮箱", max_length=256)
    uuid = fields.CharField(description="UUID", max_length=128)
    port = fields.IntField(description="端口", index=True)
    method = fields.CharField(description="加密方法", max_length=64)
    password = fields.CharField(description="密码", unique=True, max_length=128)
    upload_traffic = fields.BigIntField(description="上传流量", default=0)
    download_traffic = fields.BigIntField(description="下载流量", default=0)
    total_traffic = fields.BigIntField(description="总流量", default=0)
    last_use_time = fields.DatetimeField(description="上次使用时间", null=True, index=True)
    conn_ip_set = IPSetField(description="连接IP", default=set(), max_length=65535)
    is_deleted = fields.BooleanField(description="是否删除", default=False, index=True)

    def __str__(self):
        return f"User-{self.id}-{self.email}"
