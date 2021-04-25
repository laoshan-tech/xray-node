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
    panel_name = fields.CharField(description="面板名称", max_length=256)
    user_id = fields.BigIntField(description="面板系统内的ID")
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
        return f"User-{self.panel_name}-{self.email}"


class Node(Model):
    id = fields.BigIntField(pk=True)
    panel_name = fields.CharField(description="面板名称", max_length=256)
    node_id = fields.BigIntField(description="面板系统内的ID")
    type = fields.CharField(description="节点类型", max_length=128)
    tag = fields.CharField(description="Inbound tag", max_length=256)
    protocol = fields.CharField(description="协议", max_length=128)
    speed_limit = fields.BigIntField(description="限速")
    cipher_type = fields.CharField(description="加密方式", max_length=64)
    listen_host = fields.CharField(description="监听Host", max_length=64)
    listen_port = fields.IntField(description="监听端口")
    alter_id = fields.IntField(description="Alter ID")
    enable_tls = fields.BooleanField(description="是否开启TLS", default=False)
    enable_proxy_protocol = fields.BooleanField(description="", default=False)
    transport_mode = fields.CharField(description="Transport", max_length=128)
    path = fields.CharField(description="Path", max_length=256)
    host = fields.CharField(description="Host", max_length=256)
    cert_path = fields.CharField(description="证书", max_length=256)
    key_path = fields.CharField(description="Key", max_length=256)

    def __str__(self):
        return f"Node-{self.panel_name}-{self.node_id}"
