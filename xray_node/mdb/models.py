from __future__ import annotations

import json
import logging
from typing import Any, Union, Type, List, Set

from tortoise import fields
from tortoise.models import Model
from tortoise.transactions import atomic

from xray_node.api import entities
from xray_node.exceptions import UnsupportedUser, NodeDataNotFound, UnsupportedNode
from xray_node.utils.consts import NodeTypeEnum

logger = logging.getLogger(__name__)


class IPSetField(fields.CharField):
    def to_db_value(self, value: Any, instance: "Union[Type[Model], Model]") -> str:
        if type(value) is not set:
            value = []
        data = json.dumps(list(value))
        if len(data) > self.max_length:
            raise ValueError("Data too long.")
        return data

    def to_python_value(self, value: Any) -> Union[Set, None]:
        if value is None:
            return value
        _v = json.loads(value)
        return set(_v)


class User(Model):
    id = fields.BigIntField(pk=True)
    node: fields.ForeignKeyRelation[Node] = fields.ForeignKeyField(
        description="节点ID", model_name="models.Node", related_name="users"
    )
    user_id = fields.BigIntField(description="面板系统内的ID")
    email = fields.CharField(description="邮箱", max_length=256)
    uuid = fields.CharField(description="UUID", default="", max_length=128)
    port = fields.IntField(description="端口", default=0, index=True)
    method = fields.CharField(description="加密方法", default="", max_length=64)
    password = fields.CharField(description="密码", default="", max_length=128)
    upload_traffic = fields.BigIntField(description="上传流量", default=0)
    download_traffic = fields.BigIntField(description="下载流量", default=0)
    total_traffic = fields.BigIntField(description="总流量", default=0)
    last_use_time = fields.DatetimeField(description="上次使用时间", auto_now=True, null=True, index=True)
    conn_ip_set = IPSetField(description="连接IP", default=set(), max_length=65535)
    is_deleted = fields.BooleanField(description="是否删除", default=False, index=True)

    def __str__(self):
        return f"User-{self.node}-{self.email}"

    @classmethod
    async def _gen_obj_from_user(
        cls, u: Union[entities.SSUser, entities.VMessUser, entities.VLessUser, entities.TrojanUser]
    ) -> User:
        """
        根据数据生成ORM对象
        :param u:
        :return:
        """
        node_obj = await Node.filter(panel_name=u.panel_name, node_id=u.node_id).first()

        if not node_obj:
            raise NodeDataNotFound(msg=f"{u.panel_name}, {u.node_id}")

        if isinstance(u, entities.SSUser):
            user_obj = cls(
                node=node_obj,
                user_id=u.user_id,
                email=u.email,
                port=u.listen_port,
                method=u.method,
                password=u.password,
            )
        elif isinstance(u, (entities.VMessUser, entities.VLessUser, entities.TrojanUser)):
            user_obj = cls(node=node_obj, user_id=u.user_id, email=u.email, uuid=u.uuid)
        else:
            raise UnsupportedUser(msg=f"{type(u).__name__}")

        return user_obj

    @classmethod
    def _create_or_update_from_data(
        cls,
        data: Union[entities.SSUser, entities.VMessUser, entities.VLessUser, entities.TrojanUser],
    ):
        """
        根据数据创建或更新用户
        :param data:
        :return:
        """
        cls.get_or_create(user_id=data.user_id)

    @classmethod
    @atomic()
    async def create_or_update_from_data_list(
        cls,
        user_data_list: List[Union[entities.SSUser, entities.VMessUser, entities.VLessUser, entities.TrojanUser]],
    ):
        """
        根据数据列表创建或更新用户
        :param user_data_list:
        :return:
        """
        if await cls.all().count() < 1:
            logger.info(f"User表内无数据，全量插入")
            new_users = [await cls._gen_obj_from_user(u=u) for u in user_data_list]
            await cls.bulk_create(objects=new_users)
        else:
            db_user_dict = {
                f"{u.node.panel_name}-{u.user_id}": u
                for u in await cls.filter(is_deleted=False).prefetch_related("node").all()
            }
            enabled_user_ids = []
            need_update_or_create_users = []

            for user_data in user_data_list:
                old_db_user = db_user_dict.get(f"{user_data.panel_name}-{user_data.user_id}")
                if (
                    not old_db_user
                    or old_db_user.port != user_data.listen_port
                    or old_db_user.password != user_data.password
                    or old_db_user.method != user_data.method
                    or old_db_user.uuid != user_data.uuid
                ):
                    need_update_or_create_users.append(user_data)

            for u in need_update_or_create_users:
                cls._create_or_update_from_data(data=u)


class Node(Model):
    id = fields.BigIntField(pk=True)
    panel_name = fields.CharField(description="面板名称", max_length=256)
    node_id = fields.BigIntField(description="面板系统内的ID")
    type = fields.CharField(description="节点类型", max_length=128)
    tag = fields.CharField(description="Inbound tag", max_length=256)
    protocol = fields.CharField(description="协议", max_length=128)
    speed_limit = fields.BigIntField(description="限速", default=0)
    cipher_type = fields.CharField(description="加密方式", max_length=64)
    listen_host = fields.CharField(description="监听Host", max_length=64)
    listen_port = fields.IntField(description="监听端口")
    alter_id = fields.IntField(description="Alter ID", default=4)
    enable_tls = fields.BooleanField(description="是否开启TLS", default=False)
    enable_proxy_protocol = fields.BooleanField(description="", default=False)
    transport_mode = fields.CharField(description="Transport", max_length=128, default="tcp")
    path = fields.CharField(description="Path", max_length=256, default="/ws")
    host = fields.CharField(description="Host", max_length=256)
    cert_path = fields.CharField(description="证书", max_length=256)
    key_path = fields.CharField(description="Key", max_length=256)
    is_deleted = fields.BooleanField(description="是否删除", default=False, index=True)

    def __str__(self):
        return f"Node-{self.panel_name}-{self.node_id}"

    @classmethod
    async def _gen_obj_from_node(
        cls, n: Union[entities.SSNode, entities.VMessNode, entities.VLessNode, entities.TrojanNode]
    ) -> Node:
        """
        根据数据生成ORM对象
        :param n:
        :return:
        """
        if isinstance(n, entities.SSNode):
            node_obj = cls(
                panel_name=n.panel_name,
                node_id=n.node_id,
                type=NodeTypeEnum.Shadowsocks.value,
                tag=f"{n.panel_name}-{NodeTypeEnum.Shadowsocks.value}-{n.node_id}",
                protocol=NodeTypeEnum.Shadowsocks.value,
                cipher_type="",
                listen_host=n.listen_host,
                listen_port=n.listen_port,
                host="",
                cert_path="",
                key_path="",
            )
        elif isinstance(n, entities.VMessNode):
            node_obj = cls(
                panel_name=n.panel_name,
                node_id=n.node_id,
                type=NodeTypeEnum.VMess.value,
                tag=f"{n.panel_name}-{NodeTypeEnum.VMess.value}-{n.node_id}",
                protocol=NodeTypeEnum.VMess.value,
                cipher_type="",
                listen_host=n.listen_host,
                listen_port=n.listen_port,
                alter_id=n.alter_id,
                enable_tls=n.enable_tls,
                transport_mode=n.transport,
                path=n.path,
                host=n.host,
                cert_path="",
                key_path="",
            )
        elif isinstance(n, entities.VLessNode):
            node_obj = cls(
                panel_name=n.panel_name,
                node_id=n.node_id,
                type=NodeTypeEnum.VLess.value,
                tag=f"{n.panel_name}-{NodeTypeEnum.VLess.value}-{n.node_id}",
                protocol=NodeTypeEnum.VLess.value,
                cipher_type="",
                listen_host=n.listen_host,
                listen_port=n.listen_port,
                alter_id=n.alter_id,
                enable_tls=n.enable_tls,
                transport_mode=n.transport,
                path=n.path,
                host=n.host,
                cert_path="",
                key_path="",
            )
        elif isinstance(n, entities.TrojanNode):
            node_obj = cls(
                panel_name=n.panel_name,
                node_id=n.node_id,
                type=NodeTypeEnum.Trojan.value,
                tag=f"{n.panel_name}-{NodeTypeEnum.Trojan.value}-{n.node_id}",
                protocol=NodeTypeEnum.Trojan.value,
                cipher_type="",
                listen_host=n.listen_host,
                listen_port=n.listen_port,
                host=n.host,
                cert_path="",
                key_path="",
            )
        else:
            raise UnsupportedNode(msg=f"{type(n).__name__}")

        return node_obj

    @classmethod
    def _create_or_update_from_data(
        cls,
        data: Union[entities.SSNode, entities.VMessNode, entities.VLessNode, entities.TrojanNode],
    ):
        """
        根据数据创建或更新节点
        :param data:
        :return:
        """
        cls.get_or_create(node_id=data.node_id)

    @classmethod
    @atomic()
    async def create_or_update_from_data_list(
        cls, node_data_list: List[Union[entities.SSNode, entities.VMessNode, entities.VLessNode, entities.TrojanNode]]
    ):
        """
        根据数据列表创建或更新节点
        :param node_data_list:
        :return:
        """
        if await cls.all().count() < 1:
            logger.info(f"Node表内无数据，全量插入")
            new_nodes = [await cls._gen_obj_from_node(n=n) for n in node_data_list]
            await cls.bulk_create(objects=new_nodes)
        else:
            db_node_dict = {f"{n.panel_name}-{n.node_id}": n for n in await cls.filter(is_deleted=False).all()}
            enabled_node_ids = []
            need_update_or_create_nodes = []

            for node_data in node_data_list:
                old_db_node = db_node_dict.get(f"{node_data.panel_name}-{node_data.node_id}")
                if not old_db_node:
                    need_update_or_create_nodes.append(node_data)

            for u in need_update_or_create_nodes:
                cls._create_or_update_from_data(data=u)
