import hashlib
import logging
import re
from pathlib import Path

from xray_node.utils import http, consts

logger = logging.getLogger(__name__)


def _prepare_install(install_path: Path) -> bool:
    """
    安装前的准备
    :param install_path: 指定安装目录
    :return:
    """

    try:
        if not install_path.exists():
            install_path.mkdir(mode=0o755)
        return True
    except OSError as e:
        logger.exception(f"创建 xray-node 目录失败，{e}")
        return False


def _is_installed(install_path: Path) -> bool:
    """
    检查是否已安装
    :param install_path:
    :return:
    """
    xray_bin = install_path / "xray"
    return xray_bin.exists()


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
        xray_hash_match = re.match(r"^MD5=\s+\b(.*)\b$", req.text)
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


async def _download_xray_zip(install_path: Path) -> bool:
    """
    下载xray-core
    :param install_path:
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
        xray_zip_url = f"https://github.com/XTLS/Xray-core/releases/download/{latest_tag}/Xray-linux-64.zip"
        xray_zip_hash_url = f"https://github.com/XTLS/Xray-core/releases/download/{latest_tag}/Xray-linux-64.zip.dgst"

        md5_hash = await _get_xray_zip_hash(hash_url=xray_zip_hash_url)

        target = install_path / "Xray-linux-64.zip"
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


async def install_xray(install_path: Path = None) -> bool:
    """
    安装xray-core
    :param install_path: 指定安装目录
    :return:
    """
    if install_path is None:
        path = Path.home() / "xray-node"
    else:
        path = install_path

    if not _prepare_install(install_path=path):
        return False

    if _is_installed(install_path=path):
        logger.info(f"xray-core 已经安装在 {path} 目录下")
        return True
