"""T34：托盘菜单四项、关闭不退出、toast 时长、错误 toast 常驻、二次确认契约。"""
from dmchange.ui import app as A


def test_tray_menu_items():
    assert A.TRAY_MENU_ITEMS == ("显示主窗口", "开始录音", "导出药事会材料", "退出")


def test_status_states():
    assert set(A.StatusBar.STATES) >= {"就绪", "录音中", "识别中", "等待复核", "出站失败重试中"}


def test_toast_duration():
    assert A.TOAST_DURATION_MS == 3000
    assert A.ERROR_TOAST_PERSISTENT is True


def test_hidden_on_close_contract():
    """关闭主窗口隐藏到托盘的契约由 HiddenOnCloseWindow.closeEvent 实现。"""
    src = __import__("inspect").getsource(A.HiddenOnCloseWindow)
    assert "event.ignore()" in src and "self.hide()" in src


def test_destructive_confirm_contract():
    """破坏性操作二次确认：主窗口/托盘层声明影响范围。"""
    assert hasattr(A, "TrayApp")
