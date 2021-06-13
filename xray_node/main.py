import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import click
import psutil
from loguru import logger

from xray_node.api import get_api_cls_by_name, entities
from xray_node.config import Config
from xray_node.core.xray import Xray
from xray_node.exceptions import ReportNodeStatsError, APIStatusError
from xray_node.mdb import init_db, models
from xray_node.utils.http import client
from xray_node.utils.install import XrayFile, install_xray, is_xray_installed


class XrayNode(object):
    def __init__(self, install_path: Path = None, force_update: bool = False, use_cdn: bool = False):
        self.__prepared = False
        self.install_path = install_path
        self.force_update = force_update
        self.use_cdn = use_cdn
        self.xray_f = XrayFile(install_path=self.install_path)
        self.api_cls = None

    def __init_config(self) -> None:
        """
        读入配置文件
        :return:
        """
        self.config = Config(cfg=self.xray_f.xn_cfg_fn)

    def __prepare_logger(self) -> None:
        """
        初始化日志类
        :return:
        """
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }
        level = log_levels[self.config.log_level.upper()]
        logger.remove()
        logger.add(sys.stderr, level=level)

    def __init_loop(self) -> None:
        """
        初始化事件循环
        :return:
        """
        try:
            import uvloop

            logger.info("使用 uvloop 加速")
            uvloop.install()
        except ImportError:
            logger.info("使用原生 asyncio")

        self.loop = asyncio.get_event_loop()

    def __prepare(self) -> None:
        """
        预处理
        :return:
        """
        if self.__prepared:
            return

        self.__init_loop()
        self.__init_config()
        self.__prepare_logger()

        self.xray = Xray(xray_f=self.xray_f)

        self.__prepared = True

    async def __cleanup(self) -> None:
        """
        清理任务
        :return:
        """
        logger.info("正在关闭 Xray 服务")
        await self.xray.stop()
        if not client.is_closed:
            await client.aclose()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def __sync_user_from_local(self):
        """
        本地模式同步用户
        :return:
        """
        nodes = self.config.load_local_nodes()
        users = self.config.load_local_users()
        await models.Node.create_or_update_from_data_list(node_data_list=nodes)
        await models.User.create_or_update_from_data_list(user_data_list=users)

    async def __sync_user_from_remote(self):
        """
        远程模式同步用户
        :return:
        """
        if self.api_cls is None:
            cls = get_api_cls_by_name(panel_type=self.config.panel_type)
            self.api_cls = cls(endpoint=self.config.endpoint, mu_key=self.config.api_key, node_id=self.config.node_id)

        node = await self.api_cls.fetch_node_info()
        users = await self.api_cls.fetch_user_list()
        await models.Node.create_or_update_from_data_list(node_data_list=[node])
        await models.User.create_or_update_from_data_list(user_data_list=users)

    async def __report_stats(self):
        """
        向远程同步状态数据
        :return:
        """
        if self.api_cls is None:
            cls = get_api_cls_by_name(panel_type=self.config.panel_type)
            self.api_cls = cls(endpoint=self.config.endpoint, mu_key=self.config.api_key, node_id=self.config.node_id)

        try:
            await self.api_cls.report_node_stats()
        except APIStatusError as e:
            logger.error(f"上报节点状态信息API状态码异常 {e.msg}")
        except ReportNodeStatsError as e:
            logger.error(f"上报节点状态信息错误 {e.msg}")

        active_users = await models.User.filter_active_users()

        try:
            await self.api_cls.report_user_stats(
                stats_data=[
                    entities.SSPanelOnlineIPData(user_id=u.user_id, ip=json.dumps(list(u.conn_ip_set)))
                    for u in active_users
                ]
            )
        except APIStatusError as e:
            logger.error(f"上报用户状态信息API状态码异常 {e.msg}")
        except ReportNodeStatsError as e:
            logger.error(f"上报用户状态信息错误 {e.msg}")

        try:
            await self.api_cls.report_user_traffic(
                traffic_data=[
                    entities.SSPanelTrafficData(user_id=u.user_id, upload=u.upload_traffic, download=u.download_traffic)
                    for u in active_users
                ]
            )
            await models.User.reset_user_traffic()
        except APIStatusError as e:
            logger.error(f"上报用户流量信息API状态码异常 {e.msg}")
        except ReportNodeStatsError as e:
            logger.error(f"上报用户流量信息错误 {e.msg}")

    async def __user_man_cron(self):
        """
        用户管理
        :return:
        """
        while True:
            try:
                if self.config.user_mode == "local":
                    logger.info(f"使用本地配置文件 {self.config.fn} 加载用户信息")
                    await self.__sync_user_from_local()
                elif self.config.user_mode == "remote":
                    logger.info(f"使用远程服务加载用户信息")
                    await self.__report_stats()
                    await self.__sync_user_from_remote()

                await self.xray.sync_data_from_db()
            except Exception as e:
                logger.exception(f"用户管理出错 {e}")
            finally:
                await asyncio.sleep(60)

    async def __run_xray(self):
        """
        xray-core服务启动与用户管理
        :return:
        """
        if not is_xray_installed(xray_f=self.xray_f):
            logger.error(f"xray-core 未成功安装在 {self.xray_f.xray_install_path} 下，退出")
            if self.loop.is_running():
                self.loop.stop()

            return

        await init_db()
        await self.xray.start()
        await self.__user_man_cron()

    def install(self) -> None:
        """
        安装xray-core
        :return:
        """
        self.__prepare()
        self.loop.run_until_complete(
            install_xray(install_path=self.install_path, force_update=self.force_update, use_cdn=self.use_cdn)
        )

    def start(self) -> None:
        """
        启动服务
        :return:
        """
        self.__prepare()
        self.loop.create_task(self.__run_xray())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.__cleanup())
            logger.info("正在退出......")
        finally:
            self.loop.stop()
            self.loop.close()
            p = psutil.Process(pid=os.getpid())
            p.terminate()


@click.group()
def cli():
    """
    xray-node is a nice management tool for ss/vmess/vless/trojan proxy nodes based on xray-core.
    """
    pass


@cli.command()
@click.option(
    "-p",
    "--path",
    default=Path.home() / "xray-node",
    type=click.Path(file_okay=False, dir_okay=True),
    help="xray-core installation path.",
)
def run(path):
    """
    Run xray-core.
    """
    xn = XrayNode(install_path=Path(path))
    xn.start()


@cli.command()
@click.option(
    "-p",
    "--path",
    default=Path.home() / "xray-node",
    type=click.Path(file_okay=False, dir_okay=True),
    help="xray-core installation path.",
)
@click.option("--force-update", default=False, is_flag=True, help="Force update xray-core.")
@click.option("--use-cdn", default=False, is_flag=True, help="Install xray-core from CDN.")
def install(path, force_update: bool, use_cdn: bool):
    """
    Install xray-core.
    """
    xn = XrayNode(install_path=Path(path), force_update=force_update, use_cdn=use_cdn)
    xn.install()


if __name__ == "__main__":
    cli()
