from pathlib import Path

import pytest

from xray_node.utils import install


class TestInstall(object):
    path = Path.home() / "xray-node"

    def test_prepare_install(self):
        assert install._prepare_install(install_path=self.path) is True

    @pytest.mark.asyncio
    async def test_download_xray_zip(self):
        assert await install._download_xray_zip(install_path=self.path) is True
