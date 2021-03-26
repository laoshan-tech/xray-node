from pathlib import Path

from xray_node.utils import install


class TestInstall(object):
    def test_prepare_install(self):
        path = Path.home() / "xray-node"
        assert install._prepare_install(install_path=path) is True
