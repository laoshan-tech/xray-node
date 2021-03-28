import pytest

from xray_node.utils import install


class TestInstall(object):
    xray_file = install.XrayFile()

    def test_prepare_install(self):
        assert install._prepare_install(xray_f=self.xray_file) is True

    @pytest.mark.asyncio
    async def test_download_xray_zip(self):
        assert await install._download_xray_zip(xray_f=self.xray_file) is True

    @pytest.mark.asyncio
    async def test_unzip_xray(self):
        assert await install._unzip_xray_core(xray_f=self.xray_file) is True

    @pytest.mark.asyncio
    async def test_install(self):
        assert await install.install_xray(use_cdn=True) is True
