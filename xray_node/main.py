import asyncio
import logging
from pathlib import Path

import click

from xray_node.api import get_api_cls_by_name
from xray_node.config import Config
from xray_node.core.xray import Xray
from xray_node.mdb import init_db
from xray_node.utils.http import client
from xray_node.utils.install import XrayFile, install_xray, is_xray_installed

logger = logging.getLogger(__name__)


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
        logging.basicConfig(
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)s - %(message)s",
            level=level,
        )

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
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]

        await self.xray.stop()
        if not client.is_closed:
            await client.aclose()

    def __shutdown(self) -> None:
        """
        停止所有服务
        :return:
        """
        logger.info("正在关闭 Xray 服务")
        self.loop.run_until_complete(self.__cleanup())
        self.loop.stop()

    def __run_loop(self) -> None:
        """
        启动事件循环
        :return:
        """
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.__shutdown()

    async def __sync_user_from_local(self):
        """
        本地模式同步用户
        :return:
        """
        pass

    async def __sync_user_from_remote(self):
        """
        远程模式同步用户
        :return:
        """
        if self.api_cls is None:
            self.api_cls = get_api_cls_by_name(panel_type=self.config.panel_type)

        users = await self.api_cls.fetch_user_list()

    async def __user_man_cron(self):
        """
        用户管理
        :return:
        """
        if self.config.user_mode == "local":
            logger.info(f"使用本地配置文件 {self.config.fn} 加载用户信息")
            await self.__sync_user_from_local()
        elif self.config.user_mode == "remote":
            logger.info(f"使用远程服务加载用户信息")
            await self.__sync_user_from_remote()

        self.loop.call_later(60, self.loop.create_task, self.__user_man_cron())

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
        self.__run_loop()


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
