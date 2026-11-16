from app import __version__
from app.main import APP_NAME


def test_package_metadata() -> None:
    """基础安装检查。"""
    assert __version__ == "0.1.0"
    assert APP_NAME == "TicketFlow"
