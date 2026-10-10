"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.database.connection import init_database
from app.ui.main_window import LoginDialog, MainWindow


def main() -> int:
    """Initialize the database and start the Qt event loop."""
    init_database()

    application = QApplication(sys.argv)
    application.setApplicationName(
        "Мониторинг расходов ЖКХ"
    )

    login = LoginDialog()

    if login.exec() != LoginDialog.DialogCode.Accepted:
        return 0

    window = MainWindow(login.user_name, login.user_id)
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())