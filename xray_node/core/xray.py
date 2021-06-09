import asyncio
import json
import logging
from typing import Union

import grpc
import psutil
from google.protobuf import message as _message
from xray_rpc.app.proxyman import config_pb2 as proxyman_config_pb2
from xray_rpc.app.proxyman.command import (
    command_pb2_grpc as proxyman_command_pb2_grpc,
    command_pb2 as proxyman_command_pb2,
)
from xray_rpc.app.stats.command import command_pb2 as stats_command_pb2, command_pb2_grpc as stats_command_pb2_grpc
from xray_rpc.common.net import port_pb2, address_pb2
from xray_rpc.common.protocol import user_pb2
from xray_rpc.common.serial import typed_message_pb2
from xray_rpc.core import config_pb2 as core_config_pb2
from xray_rpc.proxy.shadowsocks import config_pb2 as shadowsocks_config_pb2
from xray_rpc.proxy.trojan import config_pb2 as trojan_config_pb2
from xray_rpc.proxy.vless import account_pb2 as vless_account_pb2
from xray_rpc.proxy.vless.inbound import config_pb2 as vless_inbound_config_pb2
from xray_rpc.proxy.vmess import account_pb2 as vmess_account_pb2
from xray_rpc.proxy.vmess.inbound import config_pb2 as vmess_inbound_config_pb2

from xray_node.config import Config
from xray_node.core import cfg
from xray_node.exceptions import (
    EmailExistsError,
    InboundTagNotFound,
    XrayError,
    AddressAlreadyInUseError,
    InboundTagAlreadyExists,
)
from xray_node.mdb import models
from xray_node.utils.consts import NETWORK_DICT, NodeTypeEnum, CIPHER_TYPE_DICT
from xray_node.utils.install import XrayFile

logger = logging.getLogger(__name__)


def to_typed_message(message: _message):
    return typed_message_pb2.TypedMessage(type=message.DESCRIPTOR.full_name, value=message.SerializeToString())


def ip2bytes(ip: str):
    return bytes([int(i) for i in ip.split(".")])


class Protocol(object):
    def __init__(self):
        self.message = None


class VMessInbound(Protocol):
    def __init__(self):
        """
        VMess
        """
        super(VMessInbound, self).__init__()
        self.message = to_typed_message(vmess_inbound_config_pb2.Config(user=[]))


class VLESSInbound(Protocol):
    def __init__(self):
        """
        VLESS
        """
        super(VLESSInbound, self).__init__()
        self.message = to_typed_message(
            vless_inbound_config_pb2.Config(
                clients=[],
                decryption="",
                fallbacks=[],
            )
        )


class ShadowsocksInbound(Protocol):
    def __init__(self):
        """
        Shadowsocks
        """
        super(ShadowsocksInbound, self).__init__()
        self.message = to_typed_message(
            shadowsocks_config_pb2.ServerConfig(
                users=[],
                network=[NETWORK_DICT["tcp"], NETWORK_DICT["udp"]],
            )
        )


class TrojanInbound(Protocol):
    def __init__(self):
        """
        Trojan
        """
        super(TrojanInbound, self).__init__()
        self.message = to_typed_message(
            trojan_config_pb2.ServerConfig(
                users=[],
                fallbacks=[],
            )
        )


class Xray(object):
    def __init__(self, xray_f: XrayFile):
        self.xray_f = xray_f
        self.xray_proc: Union[None, psutil.Process] = None

        self.config = Config(cfg=self.xray_f.xn_cfg_fn)
        self.xray_client = grpc.insecure_channel(target=f"{self.config.local_api_host}:{self.config.local_api_port}")

    async def get_user_upload_traffic(self, email: str, reset: bool = False) -> Union[int, None]:
        """
        获取用户上行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>uplink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_user_download_traffic(self, email: str, reset: bool = False) -> Union[int, None]:
        """
        获取用户下行流量，单位字节
        :param email: 邮箱，用于标识用户
        :param reset: 是否重置流量统计
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"user>>>{email}>>>traffic>>>downlink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_inbound_upload_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, None]:
        """
        获取特定传入连接上行流量，单位字节
        :param inbound_tag:
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>uplink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def get_inbound_download_traffic(self, inbound_tag: str, reset: bool = False) -> Union[int, None]:
        """
        获取特定传入连接下行流量，单位字节
        :param inbound_tag:
        :return:
        """
        stub = stats_command_pb2_grpc.StatsServiceStub(self.xray_client)
        try:
            resp = stub.GetStats(
                stats_command_pb2.GetStatsRequest(name=f"inbound>>>{inbound_tag}>>>traffic>>>downlink", reset=reset)
            )
            return resp.stat.value
        except grpc.RpcError:
            return None

    async def add_user(
        self,
        inbound_tag: str,
        email: str,
        level: int,
        type: str,
        password: str = "",
        cipher_type: int = 0,
        uuid: str = "",
        alter_id: int = 0,
    ):
        """
        在一个传入连接中添加一个用户
        :param inbound_tag:
        :param email:
        :param level:
        :param type:
        :param password:
        :param cipher_type:
        :param uuid:
        :param alter_id:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            if type == NodeTypeEnum.VMess.value:
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(vmess_account_pb2.Account(id=uuid, alter_id=alter_id)),
                )
            elif type == NodeTypeEnum.VLess.value:
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(vless_account_pb2.Account(id=uuid, alter_id=alter_id)),
                )
            elif type == NodeTypeEnum.Shadowsocks.value:
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(
                        shadowsocks_config_pb2.Account(password=password, cipher_type=cipher_type)
                    ),
                )
            elif type == NodeTypeEnum.Trojan.value:
                user = user_pb2.User(
                    email=email,
                    level=level,
                    account=to_typed_message(trojan_config_pb2.Account(password=password, flow="xtls-rprx-direct")),
                )
            else:
                raise XrayError(f"不支持的传入连接类型 {type}")

            stub.AlterInbound(
                proxyman_command_pb2.AlterInboundRequest(
                    tag=inbound_tag,
                    operation=to_typed_message(proxyman_command_pb2.AddUserOperation(user=user)),
                )
            )
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith(f"User {email} already exists."):
                raise EmailExistsError(detail, email)
            elif detail.endswith(f"handler not found: {inbound_tag}"):
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def remove_user(self, inbound_tag: str, email: str):
        """
        在一个传入连接中删除一个用户
        :param inbound_tag:
        :param email:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            stub.AlterInbound(
                proxyman_command_pb2.AlterInboundRequest(
                    tag=inbound_tag, operation=to_typed_message(proxyman_command_pb2.RemoveUserOperation(email=email))
                )
            )
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith(f"User {email} already exists."):
                raise EmailExistsError(detail, email)
            elif detail.endswith(f"handler not found: {inbound_tag}"):
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def add_inbound(self, inbound_tag: str, address: str, port: int, protocol: Protocol) -> None:
        """
        增加传入连接
        :param inbound_tag: 传入连接的标识
        :param address: 监听地址
        :param port: 监听端口
        :param protocol: 代理配置
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            resp = stub.AddInbound(
                proxyman_command_pb2.AddInboundRequest(
                    inbound=core_config_pb2.InboundHandlerConfig(
                        tag=inbound_tag,
                        receiver_settings=to_typed_message(
                            proxyman_config_pb2.ReceiverConfig(
                                port_range=port_pb2.PortRange(
                                    From=port,
                                    To=port,
                                ),
                                listen=address_pb2.IPOrDomain(
                                    ip=ip2bytes(address),  # 4字节或16字节
                                ),
                                allocation_strategy=None,
                                stream_settings=None,
                                receive_original_destination=None,
                                domain_override=None,
                                sniffing_settings=None,
                            )
                        ),
                        proxy_settings=protocol.message,
                    )
                )
            )
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail.endswith("address already in use"):
                raise AddressAlreadyInUseError(detail, port)
            elif detail.endswith(f"existing tag found: {inbound_tag}"):
                raise InboundTagAlreadyExists(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def remove_inbound(self, inbound_tag: str):
        """
        删除传入连接
        :param inbound_tag:
        :return:
        """
        stub = proxyman_command_pb2_grpc.HandlerServiceStub(self.xray_client)
        try:
            stub.RemoveInbound(proxyman_command_pb2.RemoveInboundRequest(tag=inbound_tag))
        except grpc.RpcError as rpc_err:
            detail = rpc_err.details()
            if detail == "not enough information for making a decision":
                raise InboundTagNotFound(detail, inbound_tag)
            else:
                raise XrayError(detail)

    async def sync_data_from_db(self):
        """
        从数据库同步节点与用户数据
        :return:
        """
        active_nodes = await models.Node.filter_active_nodes()
        for n in active_nodes:
            proto = Protocol()
            if n.type == NodeTypeEnum.Shadowsocks.value:
                proto = ShadowsocksInbound()
            elif n.type == NodeTypeEnum.VMess.value:
                proto = VMessInbound()
            elif n.type == NodeTypeEnum.VLess.value:
                proto = VLESSInbound()
            elif n.type == NodeTypeEnum.Trojan.value:
                proto = TrojanInbound()

            try:
                await self.add_inbound(
                    inbound_tag=n.inbound_tag, address=n.listen_host, port=n.listen_port, protocol=proto
                )
                logger.info(f"添加入向代理 {n.inbound_tag} 成功")
            except InboundTagAlreadyExists as e:
                logger.info(f"入向代理 {e.inbound_tag} 已存在，跳过")

        deleted_nodes = await models.Node.filter_deleted_nodes()
        for n in deleted_nodes:
            try:
                await self.remove_inbound(inbound_tag=n.inbound_tag)
                logger.info(f"删除入向代理 {n.inbound_tag} 成功")
            except InboundTagNotFound as e:
                logger.info(f"入向代理不存在 {e.inbound_tag}，跳过")

        active_users = await models.User.filter_active_users()
        for u in active_users:
            try:
                if u.node.cipher_type != "unknown":
                    method = CIPHER_TYPE_DICT.get(u.node.cipher_type, 0)
                else:
                    method = CIPHER_TYPE_DICT.get(u.method, 0)

                await self.add_user(
                    inbound_tag=u.node.inbound_tag,
                    email=u.email,
                    level=0,
                    type=u.node.type,
                    password=u.password,
                    cipher_type=method,
                    uuid=u.uuid,
                    alter_id=u.node.alter_id,
                )
                logger.info(f"添加用户 {u} 成功")
            except XrayError as e:
                logger.exception(f"添加用户 {u} 出错 {e.detail}")

    async def gen_cfg(self) -> None:
        """
        生成基础配置文件
        :return:
        """
        default_cfgs = [
            ("00_base.json", cfg.BASE_CFG),
            ("01_api.json", cfg.API_CFG),
            ("02_policy.json", cfg.POLICY_CFG),
            ("03_routing.json", cfg.ROUTING_CFG),
            ("04_inbounds.json", cfg.get_inbound_cfg(cfg_cls=self.config)),
            ("05_outbounds.json", cfg.OUTBOUNDS_CFG),
        ]

        for fn, content in default_cfgs:
            p = self.xray_f.xray_conf_dir / fn
            if not p.exists():
                with open(p, "w") as f:
                    json.dump(content, f, indent=2)

    async def is_running(self) -> bool:
        """
        检查xray-core运行
        :return:
        """
        return psutil.pid_exists(self.xray_proc.pid)

    async def start(self) -> None:
        """
        启动xray-core
        :return:
        """
        await self.gen_cfg()
        self.xray_proc = await asyncio.create_subprocess_exec(
            self.xray_f.xray_exe_fn,
            "run",
            "-confdir",
            self.xray_f.xray_conf_dir,
            stdout=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.5)
        if await self.is_running() is True:
            logger.info(f"xray-core 启动成功")
        else:
            self.xray_proc = None
            logger.warning(f"xray-core 启动失败")

    async def stop(self) -> None:
        """
        停止xray-core
        :return:
        """
        if self.xray_proc and await self.is_running():
            self.xray_proc.terminate()
        else:
            return

        await asyncio.sleep(0.5)
        if await self.is_running():
            logger.warning(f"xray-core 进程 {self.xray_proc.pid} 仍在运行，尝试 kill")
            self.xray_proc.kill()
        else:
            logger.info(f"xray-core 进程 {self.xray_proc.pid} 已停止运行")
            return

        await asyncio.sleep(0.5)
        if await self.is_running():
            logger.error(f"xray-core 进程 {self.xray_proc.pid} 仍在运行，kill 失败，需要手动处理")
        else:
            logger.info(f"xray-core 进程 {self.xray_proc.pid} 已停止运行")
            return
