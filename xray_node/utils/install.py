import hashlib
import logging
import platform
import re
import zipfile
from pathlib import Path

from xray_node.utils import http, consts

logger = logging.getLogger(__name__)


class XrayFile(object):
    def __init__(self, install_path: Path = None):
        """
        xray-core文件目录相关
        :param install_path:
        """
        if install_path is None:
            self.path = Path().home() / "xray-node"
        else:
            self.path = install_path

    @property
    def xray_install_path(self) -> Path:
        return self.path

    @property
    def xray_exe_fn(self) -> Path:
        return self.path / "xray"

    @property
    def xray_zip_fn(self) -> Path:
        p = platform.system().lower()
        arch = 64 if platform.machine().endswith("64") else 32
        return self.path / f"xray-{p}-{arch}.zip"

    @property
    def xray_download_url_fmt(self) -> str:
        p = "macos" if platform.system().lower() == "darwin" else platform.system().lower()
        arch = 64 if platform.machine().endswith("64") else 32
        return f"https://github.com/XTLS/Xray-core/releases/download/{{tag}}/Xray-{p}-{arch}.zip"

    @property
    def xray_download_hash_url_fmt(self) -> str:
        p = "macos" if platform.system().lower() == "darwin" else platform.system().lower()
        arch = 64 if platform.machine().endswith("64") else 32
        return f"https://github.com/XTLS/Xray-core/releases/download/{{tag}}/Xray-{p}-{arch}.zip.dgst"


def _prepare_install(xray_f: XrayFile) -> bool:
    """
    安装前的准备
    :param xray_f: XrayFile 对象
    :return:
    """

    try:
        if not xray_f.xray_install_path.exists():
            xray_f.xray_install_path.mkdir(mode=0o755)
        return True
    except OSError as e:
        logger.exception(f"创建 xray-node 目录失败，{e}")
        return False


def _is_installed(xray_f: XrayFile) -> bool:
    """
    检查是否已安装
    :param xray_f:
    :return:
    """
    if xray_f.xray_exe_fn.exists():
        xray_f.xray_exe_fn.chmod(mode=0o755)
        return True
    else:
        return False


async def _get_xray_zip_hash(hash_url: str) -> str:
    """
    获取压缩包hash值
    :param hash_url:
    :return:
    """
    req = await http.client.get(url=hash_url)
    if req.status_code != 200:
        xray_hash = ""
    else:
        xray_hash_match = re.match(r"^MD5=\s+\b(.*)\b$", req.text, re.MULTILINE)
        if xray_hash_match:
            xray_hash = xray_hash_match.group(1)
        else:
            xray_hash = ""

    return xray_hash


def _get_file_md5(fn: Path) -> str:
    """
    获取文件的md5值
    :param fn: 文件路径
    :return: md5校验值
    """
    m = hashlib.md5()  # 创建md5对象
    with open(fn, "rb") as fobj:
        while True:
            data = fobj.read(4096)
            if not data:
                break
            m.update(data)  # 更新md5对象

    return m.hexdigest()  # 返回md5对象


async def _download_xray_zip(xray_f: XrayFile) -> bool:
    """
    下载xray-core
    :param xray_f:
    :return:
    """
    try:
        req = await http.client.get(
            f"https://api.github.com/repos/{consts.XRAY_GITHUB_USER}/{consts.XRAY_GITHUB_REPO}/releases/latest"
        )
        if req.status_code != 200:
            logger.error(f"获取 xray-core 最新 release 版本失败，状态码 {req.status_code}")
            return False

        result = req.json()
        latest_tag = result["tag_name"]
        xray_zip_url = xray_f.xray_download_url_fmt.format(tag=latest_tag)
        xray_zip_hash_url = xray_f.xray_download_hash_url_fmt.format(tag=latest_tag)

        md5_hash = await _get_xray_zip_hash(hash_url=xray_zip_hash_url)

        target = xray_f.xray_zip_fn
        download_success = await http.download(url=xray_zip_url, target=target)
        if download_success:
            if md5_hash == _get_file_md5(fn=target):
                logger.info(f"下载 xray-core 成功，md5 校验成功")
                return True
            else:
                logger.warning(f"下载 xray-core 成功，但 md5 校验失败")
                return False
        else:
            return False
    except Exception as e:
        logger.exception(f"下载 xray-core 失败，{e}")
        return False


async def _unzip_xray_core(xray_f: XrayFile) -> bool:
    """
    解压xray-core
    :param xray_f:
    :return:
    """
    if xray_f.xray_zip_fn.exists():
        zip_file = zipfile.ZipFile(xray_f.xray_zip_fn, "r")
        for f in zip_file.namelist():
            if f not in ("LICENSE", "README.md"):
                zip_file.extract(f, xray_f.xray_zip_fn.parent)
        zip_file.close()
        return True
    else:
        logger.warning(f"{xray_f.xray_zip_fn} 不存在")
        return False


async def install_xray(install_path: Path = None, force_update: bool = False) -> bool:
    """
    安装xray-core
    :param install_path: 指定安装目录
    :param force_update: 是否强制升级，默认为否
    :return:
    """
    if install_path is None:
        path = Path.home() / "xray-node"
    else:
        path = install_path

    xray_file = XrayFile(install_path=path)

    if not _prepare_install(xray_f=xray_file):
        return False

    if force_update is False and _is_installed(xray_f=xray_file):
        logger.info(f"xray-core 已经安装在 {path} 目录下")
        return True

    if await _download_xray_zip(xray_f=xray_file) and await _unzip_xray_core(xray_f=xray_file):
        if _is_installed(xray_f=xray_file):
            logger.info(f"成功安装 xray-core 至 {xray_file.xray_install_path}")
            return True
        else:
            return False
    else:
        return False
