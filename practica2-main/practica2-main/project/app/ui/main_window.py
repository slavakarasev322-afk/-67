"""Main PySide6 interface for the ЖКХ application."""

from __future__ import annotations

from io import BytesIO
import pyotp
import qrcode
from PySide6.QtGui import QPixmap, QImage

from app.database.connection import get_connection


from datetime import datetime, timedelta
from app.services.account_service import _password_material
import hmac
import hashlib
import json
import re
import secrets
import getpass
import platform
import socket
from html import escape as xml_escape
import math
from zipfile import ZIP_DEFLATED, ZipFile

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSettings, QTimer, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPageLayout,
    QPageSize,
    QPen,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.account_service import (
    authenticate_user,
    get_demo_user,
    import_legacy_user,
    initialize_auth_schema,
    register_user,
    update_user_name,
    get_user_2fa_info,
    update_user_2fa,
)
from app.services.user_data_service import (
    create_meter as create_meter_for_user,
    create_property as create_property_for_user,
    create_reading as create_reading_for_user,
    list_meters as list_meters_for_user,
    list_properties as list_properties_for_user,
    list_readings as list_readings_for_user,
    remove_meter as remove_meter_for_user,
)


NAVY = "#203f91"
NAVY_DARK = "#172d68"
PINK = "#f9dddd"
PINK_ACTIVE = "#ead0d8"
BACKGROUND = "#f5f7fa"
WHITE = "#ffffff"
TEXT = "#111827"
MUTED = "#6b7280"
GREEN = "#00b979"
RED = "#ff4b4b"
YELLOW = "#ffc400"
BLUE = "#2955d9"
GRAY_BLUE = "#8392aa"


class LoginDialog(QDialog):
    """Login dialog based on the provided UI mockup."""

    def __init__(self) -> None:
        """Initialize the login dialog."""
        super().__init__()

        self.settings = QSettings("JKHApp", "MonitoringExpenses")
        initialize_auth_schema()
        self._migrate_legacy_users()
        self.user_id: int | None = None
        self.user_name = self.settings.value("user/name", "", type=str)

        self.setWindowTitle("Мониторинг расходов ЖКХ")
        self.setFixedSize(560, 620)

        self.setStyleSheet(
            """
            QDialog {
                background: #f5f7fa;
            }

            QFrame#loginCard {
                background: white;
                border: 1px solid #111827;
                border-radius: 18px;
            }

            QLabel#loginTitle {
                color: #111827;
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#loginSubtitle {
                color: #6b7b9a;
                font-size: 14px;
            }

            QLabel {
                color: #111827;
            }

            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px;
                background: white;
            }

            QPushButton {
                background: #203f91;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }

            QPushButton:hover {
                background: #172d68;
            }

            QPushButton#secondary {
                background: white;
                color: #203f91;
                border: 1px solid #203f91;
            }

            QLabel#link {
                color: #203f91;
            }
            """
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(60, 38, 60, 38)

        card = QFrame()
        card.setObjectName("loginCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 30, 42, 28)
        card_layout.setSpacing(10)

        title = QLabel("Мониторинг расходов ЖКХ")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Вход в систему")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addSpacing(8)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(15)

        name_label = QLabel("Ваше имя")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите ваше имя")
        self.name_input.setText(self.user_name)
        card_layout.addWidget(name_label)
        card_layout.addWidget(self.name_input)

        login_label = QLabel("Логин")
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Введите логин")

        password_label = QLabel("Пароль")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        card_layout.addWidget(login_label)
        card_layout.addWidget(self.login_input)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_input)

        card_layout.addSpacing(15)

        registration_button = QPushButton("Регистрация")
        registration_button.setObjectName("secondary")
        registration_button.clicked.connect(self._registration)

        login_button = QPushButton("Войти в аккаунт")
        login_button.clicked.connect(self._login)

        or_label = QLabel("Или")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gosuslugi_button = QPushButton("Войти через гос.услуги")
        gosuslugi_button.clicked.connect(self._gosuslugi)

        card_layout.addWidget(registration_button)
        card_layout.addSpacing(12)
        card_layout.addWidget(login_button)
        card_layout.addWidget(or_label)
        card_layout.addWidget(gosuslugi_button)

        outer_layout.addStretch()
        outer_layout.addWidget(card)
        outer_layout.addStretch()

        card_layout.addWidget(registration_button)
        card_layout.addSpacing(12)
        card_layout.addWidget(login_button)
        card_layout.addWidget(or_label)
        card_layout.addWidget(gosuslugi_button)

        # === Добавляем метку для ошибки (по умолчанию скрыта) ===
        self.error_label = QLabel("Неправильный логин или пароль")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #ff4b4b; font-size: 13px; font-weight: 600; margin-top: 5px;")
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        self.login_input.textChanged.connect(self._clear_error_style)
        self.password_input.textChanged.connect(self._clear_error_style)

        # В демонстрационном режиме доступны demo/demo. Если на компьютере
        # зарегистрирован пользователь, подставляем его логин, но не пароль.
        saved_login = self.settings.value("auth/last_login", "", type=str)
        if saved_login:
            self.login_input.setText(saved_login)
            self.password_input.clear()
        else:
            self.login_input.setText("demo")
            self.password_input.setText("demo")


    def _clear_error_style(self) -> None:
        """Сбрасывает красную рамку полей и скрывает текст ошибки."""
        self.error_label.hide()
        # Возвращаем стандартный стиль полей ввода
        default_style = """
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px;
                background: white;
            }
        """
        self.login_input.setStyleSheet(default_style)
        self.password_input.setStyleSheet(default_style)

    def _migrate_legacy_users(self) -> None:
        """Move accounts saved by earlier app versions from QSettings into SQLite."""
        raw = self.settings.value("auth/users_json", "[]", type=str)
        try:
            users = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            users = []
        if isinstance(users, list):
            for user in users:
                if isinstance(user, dict):
                    import_legacy_user(user)
        # Credentials are now stored in the database, not in application preferences.
        self.settings.remove("auth/users_json")
        self.settings.sync()

    def _login(self) -> None:
        """Authenticate against the SQLite user table."""
        login = self.login_input.text().strip()
        password = self.password_input.text()
        account = authenticate_user(login, password)
        
        if account is None:
            # === ВКЛЮЧАЕМ КРАСНУЮ ПОДСВЕТКУ И ОШИБКУ КАК НА МАКЕТЕ ===
            error_style = """
                QLineEdit {
                    border: 1.5px solid #ff4b4b;
                    border-radius: 6px;
                    padding: 10px;
                    background: white;
                }
            """
            self.login_input.setStyleSheet(error_style)
            self.password_input.setStyleSheet(error_style)
            self.error_label.show()
            return

        # Гарантируем корректный целочисленный ID пользователя
        user_id = int(account.get("id") or account.get("UserID") or 0)

        # === ПРОВЕРКА 2FA (если настроена) ===
        is_2fa_enabled, totp_secret = get_user_2fa_info(user_id)
        if is_2fa_enabled and totp_secret:
            code, ok = QInputDialog.getText(
                self,
                "Двухфакторная аутентификация (2FA)",
                "Введите 6-значный код из приложения-аутентификатора:",
                QLineEdit.EchoMode.Normal
            )
            if not ok or not code.strip():
                return  # Отмена ввода 2FA

            totp = pyotp.TOTP(totp_secret)
            if not totp.verify(code.strip(), valid_window=1):
                QMessageBox.warning(
                    self,
                    "Ошибка входа",
                    "Неверный или просроченный код двухфакторной аутентификации.",
                )
                return

        # Успешный вход — сохраняем сессию
        self.user_id = user_id
        if login.casefold() == "demo" and password == "demo":
            entered_name = self.name_input.text().strip()
            self.user_name = entered_name or str(account.get("name") or "Демо Пользователь")
        else:
            self.user_name = str(account.get("name") or "Пользователь")
            self.name_input.setText(self.user_name)

        self.settings.setValue("user/id", self.user_id)
        self.settings.setValue("user/name", self.user_name)
        self.settings.setValue("user/email", str(account.get("email", "")))
        self.settings.setValue("auth/last_login", str(account.get("login", login)))
        self.settings.sync()
        self.accept()

    def _registration(self) -> None:
        """Open registration form and continue to the app after sign-up."""
        registration = RegistrationDialog(self.settings, self)
        if registration.exec() == QDialog.DialogCode.Accepted:
            account = registration.registered_user
            if account:
                self.user_id = int(account["id"])
                self.user_name = str(account["name"])
                self.name_input.setText(self.user_name)
                self.login_input.setText(str(account["login"]))
                self.settings.setValue("user/name", self.user_name)
                self.settings.setValue("user/email", str(account["email"]))
                self.settings.setValue("auth/last_login", str(account["login"]))
                self.settings.sync()
                # Регистрация завершена: закрываем окно входа и открываем приложение.
                self.accept()

    def _gosuslugi(self) -> None:
        """Show the external authorization information."""
        QMessageBox.information(
            self,
            "Госуслуги",
            "Демонстрационная кнопка авторизации через Госуслуги.",
        )


class RegistrationDialog(QDialog):
    """Registration form styled after the supplied Figma mockup."""

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.registered_user: dict[str, object] | None = None

        self.setWindowTitle("Создать аккаунт — Мониторинг расходов ЖКХ")
        self.setFixedSize(520, 700)
        self.setStyleSheet(
            """
            QDialog { background: #f5f7fa; }
            QFrame#registrationCard {
                background: white;
                border: 1px solid #111827;
                border-radius: 18px;
            }
            QLabel { color: #111827; font-size: 12px; }
            QLabel#registrationTitle {
                font-size: 21px;
                font-weight: 700;
            }
            QLabel#registrationSubtitle {
                color: #6b7b9a;
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #6b7280;
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 20px;
                background: white;
                color: #111827;
            }
            QPushButton {
                background: #203f91;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 9px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background: #172d68; }
            QPushButton#secondary {
                background: white;
                color: #203f91;
                border: 1px solid #203f91;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(42, 28, 42, 28)

        card = QFrame()
        card.setObjectName("registrationCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 22, 36, 22)
        card_layout.setSpacing(7)

        title = QLabel("Мониторинг расходов ЖКХ")
        title.setObjectName("registrationTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Создать аккаунт")
        subtitle.setObjectName("registrationSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addSpacing(2)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(7)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите имя и фамилию")
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Придумайте логин")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@example.com")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Не менее 8 символов")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_repeat_input = QLineEdit()
        self.password_repeat_input.setPlaceholderText("Повторите пароль")
        self.password_repeat_input.setEchoMode(QLineEdit.EchoMode.Password)

        fields = [
            ("Имя", self.name_input),
            ("Логин", self.login_input),
            ("Email", self.email_input),
            ("Пароль", self.password_input),
            ("Повторить пароль", self.password_repeat_input),
        ]
        for label_text, field in fields:
            label = QLabel(label_text)
            card_layout.addWidget(label)
            card_layout.addWidget(field)

        card_layout.addSpacing(10)
        create_button = QPushButton("Создать аккаунт")
        create_button.setFixedWidth(180)
        card_layout.addWidget(create_button, 0, Qt.AlignmentFlag.AlignHCenter)
        create_button.clicked.connect(self._create_account)

        or_label = QLabel("Или")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(or_label)

        gosuslugi_button = QPushButton("Войти через гос.услуги")
        gosuslugi_button.setObjectName("secondary")
        gosuslugi_button.setFixedWidth(220)
        card_layout.addWidget(gosuslugi_button, 0, Qt.AlignmentFlag.AlignHCenter)
        gosuslugi_button.clicked.connect(self._gosuslugi)

        outer.addWidget(card)

    def _users(self) -> list[dict[str, str]]:
        raw = self.settings.value("auth/users_json", "[]", type=str)
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _create_account(self) -> None:
        name = self.name_input.text().strip()
        login = self.login_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        password_repeat = self.password_repeat_input.text()

        if not all([name, login, email, password, password_repeat]):
            QMessageBox.warning(self, "Не все поля заполнены", "Заполни все поля формы.")
            return
        if len(login) < 3:
            QMessageBox.warning(self, "Некорректный логин", "Логин должен содержать минимум 3 символа.")
            return
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            QMessageBox.warning(self, "Некорректный Email", "Введи корректный адрес электронной почты.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Слабый пароль", "Пароль должен содержать минимум 8 символов.")
            return
        if password != password_repeat:
            QMessageBox.warning(self, "Пароли не совпадают", "Повтори пароль точно так же, как в первом поле.")
            return

        try:
            account = register_user(name, login, email, password)
        except ValueError as error:
            QMessageBox.warning(self, "Не удалось создать аккаунт", str(error))
            return
        except Exception as error:
            QMessageBox.warning(
                self,
                "Ошибка базы данных",
                f"Аккаунт не создан. Проверьте подключение к SQLite.\n\n{error}",
            )
            return

        self.registered_user = account
        self.settings.setValue("user/name", name)
        self.settings.setValue("user/email", email)
        self.settings.setValue("auth/last_login", login)
        self.settings.sync()
        self.accept()

    def _gosuslugi(self) -> None:
        QMessageBox.information(
            self,
            "Госуслуги",
            "Вход через Госуслуги пока демонстрационный и не подключён к внешней авторизации.",
        )


class DonutChart(QWidget):
    """Cost distribution chart built from actual calculations or tariff estimates."""

    COLORS = {
        "Газ": QColor("#718096"),
        "Вода": QColor("#2955d9"),
        "Электроэнергия": QColor("#ffc400"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(300, 235)
        self.values: dict[str, float] = {name: 0.0 for name in self.COLORS}

    def set_data(self, values: dict[str, float]) -> None:
        self.values = {name: max(0.0, float(values.get(name, 0) or 0)) for name in self.COLORS}
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = min(self.width() * 0.70, self.height() * 0.82)
        radius = width / 2
        center_x = self.width() * 0.43
        center_y = self.height() * 0.50
        rect = (int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2))
        total = sum(self.values.values())

        if total <= 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#e5e7eb"))
            painter.drawEllipse(*rect)
            inner_radius = radius * 0.62
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(
                int(center_x - inner_radius), int(center_y - inner_radius),
                int(inner_radius * 2), int(inner_radius * 2),
            )
            painter.setPen(QColor("#6b7280"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(
                int(center_x - inner_radius), int(center_y - 12),
                int(inner_radius * 2), 24,
                Qt.AlignmentFlag.AlignCenter, "Нет данных",
            )
            painter.end()
            return

        start_angle = 90 * 16
        for name, color in self.COLORS.items():
            value = self.values.get(name, 0.0)
            if value <= 0:
                continue
            span_angle = int(360 * 16 * value / total)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawPie(*rect, start_angle, span_angle)
            start_angle += span_angle

        inner_radius = radius * 0.62
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(
            int(center_x - inner_radius), int(center_y - inner_radius),
            int(inner_radius * 2), int(inner_radius * 2),
        )
        painter.end()


class ResourceBars(QWidget):
    """Monthly consumption chart based on saved meter readings."""

    COLORS = {
        "Газ": QColor("#8392aa"),
        "Электроэнергия": QColor("#ffc400"),
        "Вода": QColor("#29458f"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(205)
        self.months: list[str] = []
        self.series: dict[str, list[float]] = {
            "Газ": [],
            "Электроэнергия": [],
            "Вода": [],
        }
        self.set_data([], {})

    def set_data(
        self,
        months: list[str],
        series: dict[str, list[float]],
    ) -> None:
        """Update chart data. Values are consumptions from SQLite readings."""
        self.months = list(months)
        self.series = {
            name: [max(0.0, float(value or 0)) for value in series.get(name, [])]
            for name in self.COLORS
        }
        for name in self.series:
            if len(self.series[name]) < len(self.months):
                self.series[name].extend([0.0] * (len(self.months) - len(self.series[name])))
            else:
                self.series[name] = self.series[name][:len(self.months)]
        if self.months:
            lines = []
            for index, month in enumerate(self.months):
                parts = [f"{name}: {self.series[name][index]:g}" for name in self.series]
                lines.append(f"{month}: " + "; ".join(parts))
            self.setToolTip("Потребление по сохранённым показаниям\n" + "\n".join(lines))
        else:
            self.setToolTip("Нет сохранённых данных для графика")
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        values = [v for row in self.series.values() for v in row]
        max_value = max(values, default=0.0)
        if not self.months or max_value <= 0:
            painter.setPen(QColor("#6b7280"))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Пока недостаточно показаний для графика",
            )
            painter.end()
            return

        left, right = 28, max(29, self.width() - 28)
        top, bottom = 24, max(25, self.height() - 38)
        plot_height = bottom - top
        available_width = max(1, right - left)
        month_width = available_width / len(self.months)
        names = list(self.COLORS)
        slot_width = month_width / len(names)
        bar_width = max(3, min(19, slot_width * 0.58))

        # Baseline
        painter.setPen(QPen(QColor("#d9dee8"), 1))
        painter.drawLine(int(left), int(bottom), int(right), int(bottom))

        for month_index, month in enumerate(self.months):
            group_center = left + month_width * (month_index + 0.5)
            for series_index, name in enumerate(names):
                value = self.series[name][month_index]
                if value <= 0:
                    continue
                height = max(1.0, value / max_value * (plot_height - 6))
                center_x = left + month_width * month_index + slot_width * (series_index + 0.5)
                x = center_x - bar_width / 2
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self.COLORS[name]))
                painter.drawRoundedRect(
                    int(x), int(bottom - height), int(bar_width), int(height), 4, 4
                )

            painter.setPen(QColor(TEXT))
            painter.setFont(QFont("Arial", 9))
            label_rect = painter.boundingRect(
                int(group_center - month_width / 2), int(bottom + 7),
                int(month_width), 22,
                Qt.AlignmentFlag.AlignCenter,
                month,
            )
            painter.drawText(label_rect, month)

        painter.end()


class SettingsIcon(QWidget):
    """Small, colorful vector icons inspired by the supplied UI mockup.

    The icons are painted with Qt rather than emoji glyphs, so they render
    consistently on Linux even when color emoji fonts are unavailable.
    """

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(44, 44)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAccessibleName({
            "profile": "Профиль",
            "security": "Безопасность",
            "property": "Выбор жилья",
            "notifications": "Уведомления",
            "bank": "Банковские карты",
        }.get(kind, "Настройка"))

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(self.width() / 44.0, self.height() / 44.0)
        painter.setPen(Qt.PenStyle.NoPen)

        # Soft pink tile matches the application's sidebar and reference UI.
        painter.setBrush(QColor("#fff0f2"))
        painter.drawRoundedRect(QRectF(1, 1, 42, 42), 10, 10)

        if self.kind == "profile":
            # Head and hair.
            painter.setBrush(QColor("#f4b183"))
            painter.drawEllipse(QRectF(16, 7, 12, 13))
            hair = QPainterPath()
            hair.moveTo(15.5, 14.5)
            hair.cubicTo(13.5, 7.0, 20.0, 4.5, 26.8, 8.0)
            hair.cubicTo(30.0, 9.8, 29.3, 13.2, 28.5, 15.0)
            hair.lineTo(26.0, 11.0)
            hair.cubicTo(22.5, 13.0, 19.0, 12.3, 15.5, 14.5)
            hair.closeSubpath()
            painter.setBrush(QColor("#5d382b"))
            painter.drawPath(hair)
            # Orange shirt with blue jacket details.
            torso = QPainterPath()
            torso.moveTo(13, 36)
            torso.lineTo(14.5, 26)
            torso.cubicTo(15.5, 22.5, 19, 21, 22, 21)
            torso.cubicTo(25.5, 21, 29, 23, 30, 26)
            torso.lineTo(31.5, 36)
            torso.closeSubpath()
            gradient = QLinearGradient(13, 22, 32, 37)
            gradient.setColorAt(0, QColor("#ffb52e"))
            gradient.setColorAt(1, QColor("#f07822"))
            painter.setBrush(gradient)
            painter.drawPath(torso)
            painter.setBrush(QColor("#2f72d6"))
            jacket = QPainterPath()
            jacket.moveTo(15, 25)
            jacket.lineTo(19, 23)
            jacket.lineTo(21, 36)
            jacket.lineTo(14, 36)
            jacket.closeSubpath()
            jacket.moveTo(29, 25)
            jacket.lineTo(25, 23)
            jacket.lineTo(23, 36)
            jacket.lineTo(30, 36)
            jacket.closeSubpath()
            painter.drawPath(jacket)
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(21.1, 25, 1.8, 1.8))
            painter.drawEllipse(QRectF(21.1, 29, 1.8, 1.8))

        elif self.kind == "security":
            shield = QPainterPath()
            shield.moveTo(22, 5.5)
            shield.lineTo(34, 10)
            shield.lineTo(32.5, 23)
            shield.cubicTo(31.3, 28.5, 26.5, 33.5, 22, 37)
            shield.cubicTo(17.5, 33.5, 12.7, 28.5, 11.5, 23)
            shield.lineTo(10, 10)
            shield.closeSubpath()
            gradient = QLinearGradient(10, 6, 34, 37)
            gradient.setColorAt(0, QColor("#42a5ff"))
            gradient.setColorAt(0.55, QColor("#1874e8"))
            gradient.setColorAt(1, QColor("#1547b8"))
            painter.setBrush(gradient)
            painter.drawPath(shield)
            highlight = QPainterPath()
            highlight.moveTo(22, 9)
            highlight.lineTo(30, 12)
            highlight.lineTo(29, 22)
            highlight.cubicTo(28, 26, 25, 29.5, 22, 32)
            highlight.closeSubpath()
            painter.setBrush(QColor(255, 255, 255, 42))
            painter.drawPath(highlight)
            painter.setPen(QPen(QColor("#d9f0ff"), 1.8, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(QPointF(17.5, 21.5), QPointF(21, 25))
            painter.drawLine(QPointF(21, 25), QPointF(27, 17.5))

        elif self.kind == "property":
            # Small tree next to a warm-colored house.
            painter.setBrush(QColor("#8a542e"))
            painter.drawRoundedRect(QRectF(8, 22, 3.5, 13), 1, 1)
            painter.setBrush(QColor("#3eaa56"))
            painter.drawEllipse(QRectF(4, 11, 12, 12))
            painter.drawEllipse(QRectF(8, 7, 10, 12))
            painter.setBrush(QColor("#79c94e"))
            painter.drawEllipse(QRectF(5, 9, 9, 9))
            painter.drawEllipse(QRectF(10, 12, 8, 8))
            house = QPainterPath()
            house.moveTo(15, 21)
            house.lineTo(25, 12)
            house.lineTo(36, 21)
            house.lineTo(33, 21)
            house.lineTo(33, 35)
            house.lineTo(18, 35)
            house.lineTo(18, 21)
            house.closeSubpath()
            painter.setBrush(QColor("#ffe29a"))
            painter.drawPath(house)
            roof = QPainterPath()
            roof.moveTo(13.5, 21)
            roof.lineTo(25, 10)
            roof.lineTo(37.5, 21)
            roof.lineTo(34, 21)
            roof.lineTo(25, 13.2)
            roof.lineTo(17, 21)
            roof.closeSubpath()
            painter.setBrush(QColor("#ef5350"))
            painter.drawPath(roof)
            painter.setBrush(QColor("#4a8fe7"))
            painter.drawRoundedRect(QRectF(23, 25, 5, 10), 1, 1)
            painter.setBrush(QColor("#8ed5ff"))
            painter.drawRect(QRectF(19.5, 23, 3, 3))
            painter.drawRect(QRectF(29, 23, 3, 3))

        elif self.kind == "notifications":
            # Golden bell, orange rim and clapper.
            bell = QPainterPath()
            bell.moveTo(11, 29)
            bell.cubicTo(14, 26, 14.5, 22, 14.5, 17)
            bell.cubicTo(14.5, 11, 18, 8, 22, 8)
            bell.cubicTo(26, 8, 29.5, 11, 29.5, 17)
            bell.cubicTo(29.5, 22, 30, 26, 33, 29)
            bell.closeSubpath()
            gradient = QLinearGradient(11, 9, 32, 31)
            gradient.setColorAt(0, QColor("#ffe45c"))
            gradient.setColorAt(0.65, QColor("#ffbf00"))
            gradient.setColorAt(1, QColor("#f59e0b"))
            painter.setBrush(gradient)
            painter.drawPath(bell)
            painter.setBrush(QColor("#f28b16"))
            painter.drawRoundedRect(QRectF(10, 28, 24, 3.8), 1.8, 1.8)
            painter.drawEllipse(QRectF(19, 32, 6, 5))
            painter.setBrush(QColor("#fff5b8"))
            painter.drawEllipse(QRectF(17.5, 11, 3.2, 7))
            painter.setBrush(QColor("#fca311"))
            painter.drawEllipse(QRectF(27, 5, 7, 7))
            painter.setBrush(QColor("#ffcc33"))
            painter.drawEllipse(QRectF(28.5, 3.5, 4, 4))

        elif self.kind == "bank":
            # Two overlapping payment cards with a gold chip.
            painter.save()
            painter.translate(22, 22)
            painter.rotate(-7)
            painter.setBrush(QColor("#a7d8ff"))
            painter.drawRoundedRect(QRectF(-14, -14, 30, 20), 4, 4)
            painter.setBrush(QColor("#3778e5"))
            painter.drawRoundedRect(QRectF(-17, -8, 32, 22), 4, 4)
            painter.setBrush(QColor("#2148a8"))
            painter.drawRect(QRectF(-17, -2, 32, 5))
            painter.setBrush(QColor("#ffd05a"))
            painter.drawRoundedRect(QRectF(-11, 4, 7, 5), 1.2, 1.2)
            painter.setBrush(QColor("#ffffff"))
            painter.drawRoundedRect(QRectF(4, 6, 7, 2), 1, 1)
            painter.restore()

        painter.end()


class FormatDownloadButton(QPushButton):
    """Outlined download button with a colored format badge on the right."""

    def __init__(
        self,
        label: str,
        format_name: str,
        badge_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(label, parent)
        self.label_text = label
        self.format_name = format_name
        self.badge_color = QColor(badge_color)
        self.setMinimumHeight(42)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{label} — {format_name}")
        self.setStyleSheet("background: transparent; border: none; padding: 0;")

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self.isDown():
            background = QColor("#f1f5f9")
        elif self.underMouse():
            background = QColor("#f8fafc")
        else:
            background = QColor("#ffffff")

        painter.setPen(QPen(QColor("#111827"), 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 6, 6)

        badge_width = 48 if self.format_name.upper() == "PDF" else 54
        badge_height = 22
        badge_rect = QRectF(
            self.width() - badge_width - 12,
            (self.height() - badge_height) / 2,
            badge_width,
            badge_height,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.badge_color)
        painter.drawRoundedRect(badge_rect, 4, 4)

        label_rect = QRectF(
            10,
            0,
            max(1, self.width() - badge_width - 28),
            self.height(),
        )
        painter.setPen(QColor("#111827"))
        label_font = QFont(self.font())
        label_font.setPixelSize(13)
        painter.setFont(label_font)
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.label_text,
        )

        painter.setPen(QColor("#ffffff"))
        badge_font = QFont(self.font())
        badge_font.setPixelSize(11)
        badge_font.setBold(True)
        painter.setFont(badge_font)
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.format_name.upper(),
        )
        painter.end()


class MainWindow(QMainWindow):
    """Main application window matching the supplied mockups."""

    page_changed = Signal(int)

    def __init__(self, user_name: str, user_id: int | None = None) -> None:
        """Initialize the main window for a single authenticated user."""
        super().__init__()

        self.user_name = user_name
        self.user_id = int(user_id) if user_id is not None else int(get_demo_user()["id"])
        self.user_settings = QSettings("JKHApp", "MonitoringExpenses")
        self.current_property_id: int | None = None

        self.history_page = 1
        self.history_page_size = 10
        self.history_rows = []

        # Банковские карты хранятся в памяти приложения.
        self.bank_cards: list[dict[str, object]] = [
            {"bank": "СберБанк", "number": "0000 0000 0000 0000", "expiry": "00/00", "main": True},
            {"bank": "ВТБ", "number": "0000 0000 0000 0000", "expiry": "00/00", "main": False},
        ]

        self.setWindowTitle("Мониторинг расходов ЖКХ")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self._apply_style()

        self.stack = QStackedWidget()

        self.nav_buttons: list[QPushButton] = []

        self._build_layout()
        self._create_pages()
        selected_id = self.address_combo.currentData()
        self.current_property_id = (
            int(selected_id) if selected_id is not None else None
        )
        self._load_meters()

        self._set_active_navigation(0)

    def _apply_style(self) -> None:
        """Apply the global application stylesheet."""
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f7fa;
            }

            QWidget {
                font-family: Arial;
                font-size: 14px;
                color: #111827;
            }

            #sidebar {
                background: #f9dddd;
                border: none;
            }

            #userName {
                font-size: 17px;
                font-weight: 700;
            }

            #roleLabel {
                color: #00b979;
                font-weight: 700;
            }

            QPushButton#navButton {
                background: transparent;
                color: #111827;
                border: none;
                text-align: left;
                padding: 11px 16px;
                font-size: 13px;
                font-weight: 600;
                border-radius: 6px;
            }

            QPushButton#navButton:hover {
                background: #f0d5dc;
            }

            QPushButton#navButton[active="true"] {
                background: #ead0d8;
                color: #203f91;
            }

            #content {
                background: #f5f7fa;
            }

            #topBar {
                background: white;
                border-bottom: 1px solid #eef0f4;
            }

            QLabel#pageTitle {
                font-size: 21px;
                font-weight: 700;
            }

            QLabel#cardTitle {
                font-weight: 700;
            }

            QLabel#bigValue {
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#redValue {
                color: #ff4b4b;
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#greenValue {
                color: #00b979;
                font-size: 18px;
                font-weight: 700;
            }

            QFrame#card {
                background: white;
                border: none;
                border-radius: 8px;
            }

            QFrame#whitePanel {
                background: white;
                border-radius: 8px;
            }

            QLineEdit,
            QComboBox {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 18px;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 1px solid #2955d9;
            }

            QPushButton#primaryButton {
                background: #203f91;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 10px 18px;
                font-weight: 700;
            }

            QPushButton#primaryButton:hover {
                background: #172d68;
            }

            QPushButton#outlineButton {
                background: white;
                color: #111827;
                border: 1px solid #111827;
                border-radius: 6px;
                padding: 8px 14px;
            }

            QPushButton#settingButton {
                background: #dbe2f0;
                border: none;
                border-radius: 5px;
                padding: 10px 14px;
                text-align: left;
                font-weight: 700;
            }

            QPushButton#settingButton:hover {
                background: #cbd5e1;
            }

            QTableWidget {
                background: white;
                border: none;
                gridline-color: #eeeeee;
                font-size: 14px;
            }

            QHeaderView::section {
                background: white;
                border: none;
                padding: 10px;
                font-size: 15px;
                font-weight: 700;
            }

            QScrollArea {
                border: none;
                background: transparent;
            }

            QCheckBox {
                spacing: 10px;
                font-weight: 600;
            }
            QPushButton#budgetButton {
                color: #203f91; background: transparent; border: none;
                text-align: left; padding: 0 2px; font-size: 12px;
            }
            QPushButton#budgetButton:hover { text-decoration: underline; }
            """
        )

    def _build_layout(self) -> None:
        """Build the main window layout."""
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        central_layout.addWidget(sidebar)

        content = QWidget()
        content.setObjectName("content")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        top_bar = self._create_top_bar()
        content_layout.addWidget(top_bar)

        content_layout.addWidget(self.stack, 1)

        central_layout.addWidget(content, 1)

        self.setCentralWidget(central)

    def _create_sidebar(self) -> QWidget:
        """Create the pink navigation sidebar."""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(204)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 28, 0, 0)
        layout.setSpacing(4)

        self.user_name_label = QLabel(self.user_name)
        self.user_name_label.setObjectName("userName")
        self.user_name_label.setWordWrap(True)
        # Немного увеличим отступы снизу для имени, так как убрали строку роли
        self.user_name_label.setContentsMargins(18, 0, 8, 18)

        # Строка с ролью полностью удалена

        layout.addWidget(self.user_name_label)

        navigation = [
            ("Главное меню", 0),
            ("Приборы учета", 1),
            ("Аналитика и прогнозы", 2),
            ("Отчеты и экспорт", 3),
            ("Настройки", 4),
        ]

        for title, index in navigation:
            button = QPushButton(title)
            button.setObjectName("navButton")
            button.setProperty("active", False)
            button.clicked.connect(
                lambda checked=False, value=index: self._navigate(value)
            )

            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        return sidebar

    def _create_top_bar(self) -> QWidget:
        """Create a database-backed address selector and reading button."""
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(64)

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(26, 0, 26, 0)
        layout.setSpacing(12)

        self.address_combo = QComboBox()
        self.address_combo.setFixedWidth(420)
        try:
            for prop in list_properties_for_user(self.user_id):
                self.address_combo.addItem(
                    str(prop["address"]), int(prop["id"])
                )
        except Exception as error:
            QMessageBox.warning(
                self, "Ошибка загрузки адресов", str(error)
            )

        if self.address_combo.count() == 0:
            self.address_combo.addItem("Адреса не добавлены", None)

        self.address_combo.currentIndexChanged.connect(
            self._on_property_changed
        )
        layout.addWidget(self.address_combo)
        layout.addStretch()

        reading_button = QPushButton("+ Внести показания")
        reading_button.setObjectName("primaryButton")
        reading_button.clicked.connect(self._open_reading_dialog)
        layout.addWidget(reading_button)

        return top_bar

    def _on_property_changed(self, index: int) -> None:
        """Refresh meters when the selected property changes."""
        property_id = self.address_combo.itemData(index)
        self.current_property_id = (
            int(property_id) if property_id is not None else None
        )
        if hasattr(self, "meter_cards_layout") and hasattr(self, "history_table"):
            self._load_meters()
        else:
            self._refresh_dashboard()

    def _reload_property_selector(
        self, selected_property_id: int | None = None
    ) -> None:
        """Reload known addresses and optionally select one."""
        properties = list_properties_for_user(self.user_id)
        self.address_combo.blockSignals(True)
        self.address_combo.clear()
        for prop in properties:
            self.address_combo.addItem(str(prop["address"]), int(prop["id"]))
        if not properties:
            self.address_combo.addItem("Адреса не добавлены", None)
            index = 0
        elif selected_property_id is None:
            index = 0
        else:
            index = self.address_combo.findData(int(selected_property_id))
            if index < 0:
                index = 0
        self.address_combo.setCurrentIndex(index)
        self.address_combo.blockSignals(False)
        current_id = self.address_combo.currentData()
        self.current_property_id = int(current_id) if current_id is not None else None
        if hasattr(self, "meter_cards_layout") and hasattr(self, "history_table"):
            self._load_meters()

    def _create_pages(self) -> None:
        """Create all main application pages."""
        self.stack.addWidget(self._dashboard_page())
        self.stack.addWidget(self._meters_page())
        self.stack.addWidget(self._analytics_page())
        self.stack.addWidget(self._reports_page())
        self.stack.addWidget(self._settings_page())

    def _navigate(self, index: int) -> None:
        """Navigate to an application page."""
        self.stack.setCurrentIndex(index)
        self._set_active_navigation(index)

        if index == 1:
            self._load_meters()

    def _set_active_navigation(self, index: int) -> None:
        """Highlight the active navigation button."""
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty(
                "active",
                button_index == index,
            )
            button.style().unpolish(button)
            button.style().polish(button)

    def _dashboard_page(self) -> QWidget:
        """Build dashboard cards and charts whose values come from stored data."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 0, 24, 24)
        layout.setSpacing(10)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        payment_card = self._stat_card(
            "К оплате", "Нет данных", "red", value_key="dashboard_payment"
        )
        budget_card = self._stat_card(
            "Месячный бюджет ЖКХ", "Не задан", "normal", value_key="dashboard_budget"
        )
        control_card = self._stat_card(
            "Технический контроль", "Нет данных", "green", value_key="dashboard_control"
        )
        cards_layout.addWidget(payment_card, 1)
        cards_layout.addWidget(budget_card, 1)
        cards_layout.addWidget(control_card, 1)

        budget_button = QPushButton("Задать бюджет" )
        budget_button.setObjectName("budgetButton")
        budget_button.setCursor(Qt.CursorShape.PointingHandCursor)
        budget_button.clicked.connect(self._set_dashboard_budget)
        budget_card.layout().addWidget(budget_button)
        self.dashboard_budget_button = budget_button

        layout.addLayout(cards_layout)

        chart_panel = QFrame()
        chart_panel.setObjectName("whitePanel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(26, 26, 26, 20)

        self.dashboard_chart_title = QLabel("Динамика потребления ресурсов")
        self.dashboard_chart_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        chart_layout.addWidget(self.dashboard_chart_title)

        self.dashboard_chart = ResourceBars()
        chart_layout.addWidget(self.dashboard_chart, 1)

        legend = QHBoxLayout()
        legend.addStretch()
        for label, color in [
            ("Газ", "#8392aa"),
            ("Электро", "#ffc400"),
            ("Вода", "#29458f"),
        ]:
            badge = QLabel(label)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(76, 36)
            badge.setStyleSheet(
                f"background: {color}; color: white; border-radius: 18px; font-weight: 700;"
            )
            legend.addWidget(badge)
        legend.addStretch()
        chart_layout.addLayout(legend)
        layout.addWidget(chart_panel, 1)
        return page

    def _stat_card(
        self,
        title: str,
        value: str,
        value_type: str,
        value_key: str | None = None,
    ) -> QFrame:
        """Create a dashboard card and keep references for dynamic refresh."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(104)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        value_label = QLabel(value)
        if value_type == "red":
            value_label.setObjectName("redValue")
        elif value_type == "green":
            value_label.setObjectName("greenValue")
        else:
            value_label.setObjectName("bigValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        if value_key:
            setattr(self, value_key + "_title", title_label)
            setattr(self, value_key + "_value", value_label)
        return card

    @staticmethod
    def _parse_reading_date(value: object) -> datetime | None:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _resource_group(resource: object) -> str | None:
        name = str(resource or "").casefold()
        if "газ" in name:
            return "Газ"
        if "электр" in name or "electric" in name:
            return "Электроэнергия"
        if "вод" in name or "water" in name:
            return "Вода"
        return None

    @staticmethod
    def _month_start(year: int, month: int) -> tuple[str, str]:
        start = f"{year:04d}-{month:02d}-01"
        if month == 12:
            next_start = f"{year + 1:04d}-01-01"
        else:
            next_start = f"{year:04d}-{month + 1:02d}-01"
        return start, next_start

    @staticmethod
    def _month_title(year: int, month: int) -> str:
        names = [
            "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
        ]
        return f"{names[month - 1]} {year}"

    @staticmethod
    def _money(value: float) -> str:
        return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " ₽"

    def _charges_for_month(
        self,
        property_id: int,
        year: int,
        month: int,
        month_readings: list[dict],
    ) -> tuple[dict[str, float], dict[str, float], str]:
        """Return (all charges, unpaid charges, source status) for a month.

        Prefer saved Calculations. If there are none, calculate a clearly marked
        estimate from that property's effective Tariffs and measured consumption.
        No fake/default tariffs are used.
        """
        categories = ("Газ", "Вода", "Электроэнергия")
        all_charges = {name: 0.0 for name in categories}
        due_charges = {name: 0.0 for name in categories}
        start, next_start = self._month_start(year, month)

        try:
            with get_connection() as connection:
                calculated = connection.execute(
                    """SELECT m.Type AS MeterType, c.Amount AS Amount,
                              COALESCE(c.IsPaid, 0) AS IsPaid
                       FROM Calculations c
                       JOIN Readings r ON r.ReadingID = c.ReadingID
                       JOIN Meters m ON m.MeterID = r.MeterID
                       WHERE m.PropertyID = ?
                         AND date(r.ReadingDate) >= date(?)
                         AND date(r.ReadingDate) < date(?)""",
                    (property_id, start, next_start),
                ).fetchall()

                if calculated:
                    for row in calculated:
                        category = self._resource_group(row["MeterType"])
                        print("ROW TYPE:", row["MeterType"])
                        print("GROUP:", category)
                        print("AMOUNT:", row["Amount"])
                        if category is None:
                            continue
                        amount = max(0.0, float(row["Amount"] or 0))
                        all_charges[category] += amount
                        if not bool(row["IsPaid"]):
                            due_charges[category] += amount
                    return all_charges, due_charges, "actual"

                tariffs = connection.execute(
                    """SELECT ResourceType, Rate, ValidFrom, ValidTo
                       FROM Tariffs
                       WHERE PropertyID = ?
                         AND (ValidFrom IS NULL OR date(ValidFrom) < date(?))
                         AND (ValidTo IS NULL OR date(ValidTo) >= date(?))
                       ORDER BY date(ValidFrom) DESC""",
                    (property_id, next_start, start),
                ).fetchall()
        except Exception as e:
            print("CHARGES ERROR:", repr(e))
            return all_charges, due_charges, "unavailable"

        if not month_readings:
            return all_charges, due_charges, "no_data"
        if not tariffs:
            return all_charges, due_charges, "no_tariffs"

        # An initial reading with no previous value cannot safely yield a bill.
        if any(row.get("previous_value") is None for row in month_readings):
            return all_charges, due_charges, "need_previous"

        for reading in month_readings:
            category = self._resource_group(reading.get("meter_type"))
            if category is None:
                return all_charges, due_charges, "missing_tariff"
            meter_type = str(reading.get("meter_type") or "").strip().casefold()
            exact = [
                t for t in tariffs
                if str(t["ResourceType"] or "").strip().casefold() == meter_type
            ]
            candidates = exact or [
                t for t in tariffs
                if self._resource_group(t["ResourceType"]) == category
            ]
            if not candidates:
                return all_charges, due_charges, "missing_tariff"
            try:
                rate = max(0.0, float(candidates[0]["Rate"] or 0))
                consumption = float(reading.get("consumption") or 0)
            except (TypeError, ValueError):
                return all_charges, due_charges, "need_previous"
            charge = max(0.0, consumption) * rate
            all_charges[category] += charge
            due_charges[category] += charge

        return all_charges, due_charges, "estimate"

    def _set_dashboard_budget(self) -> None:
        """Set a separate, locally persisted budget for this user and property."""
        if self.current_property_id is None:
            QMessageBox.information(self, "Бюджет", "Сначала добавьте или выберите адрес.")
            return
        key = f"dashboard/budget/{self.user_id}/{self.current_property_id}"
        existing = self.user_settings.value(key, None)
        try:
            default_value = float(existing) if existing not in (None, "") else 0.0
        except (TypeError, ValueError):
            default_value = 0.0
        value, accepted = QInputDialog.getDouble(
            self, "Месячный бюджет ЖКХ", "Укажите бюджет на месяц (₽):",
            default_value, 0.0, 100000000.0, 2,
        )
        if accepted:
            self.user_settings.setValue(key, value)
            self.user_settings.sync()
            self._refresh_dashboard()

    def _refresh_dashboard(self) -> None:
        """Recompute dashboard and analytics visuals for the selected user's address."""
        if not hasattr(self, "dashboard_chart"):
            return

        empty_series = {"Газ": [], "Электроэнергия": [], "Вода": []}
        if self.current_property_id is None:
            self.dashboard_payment_title.setText("К оплате")
            self.dashboard_payment_value.setText("Нет адреса")
            self.dashboard_budget_value.setText("Не задан")
            self.dashboard_budget_button.setText("Задать бюджет")
            self.dashboard_control_value.setText("Нет счётчиков")
            self.dashboard_control_value.setStyleSheet("color: #6b7280; font-size: 17px; font-weight: 700;")
            self.dashboard_chart_title.setText("Динамика потребления ресурсов")
            self.dashboard_chart.set_data([], empty_series)
            if hasattr(self, "analytics_forecast_chart"):
                self.analytics_forecast_chart.set_data([], empty_series)
            self._refresh_forecast_text([], empty_series)
            self._set_analytics_charges({"Газ": 0.0, "Вода": 0.0, "Электроэнергия": 0.0}, "no_data")
            return

        property_id = int(self.current_property_id)
        try:
            readings = list_readings_for_user(property_id, self.user_id)
            meters = list_meters_for_user(property_id, self.user_id)
        except Exception:
            self.dashboard_payment_value.setText("Ошибка данных")
            self.dashboard_control_value.setText("Не удалось проверить")
            return

        parsed = []
        for reading in readings:
            dt = self._parse_reading_date(reading.get("reading_date"))
            if dt is not None:
                parsed.append((reading, dt))

        if parsed:
            latest = max(dt for _, dt in parsed)
            latest_total_month = latest.year * 12 + latest.month - 1
            month_keys = []
            for offset in range(4, -1, -1):
                total = latest_total_month - offset
                month_keys.append((total // 12, total % 12 + 1))
            month_names = [
                {1:"Янв", 2:"Фев", 3:"Мар", 4:"Апр", 5:"Май", 6:"Июн", 7:"Июл", 8:"Авг", 9:"Сен", 10:"Окт", 11:"Ноя", 12:"Дек"}[m]
                for _, m in month_keys
            ]
            by_month = {
                key: {"Газ": 0.0, "Электроэнергия": 0.0, "Вода": 0.0}
                for key in month_keys
            }
            for reading, dt in parsed:
                key = (dt.year, dt.month)
                if key not in by_month:
                    continue
                category = self._resource_group(reading.get("meter_type"))
                if category is None:
                    continue
                try:
                    consumption = float(reading.get("consumption") or 0)
                except (TypeError, ValueError):
                    consumption = 0.0
                by_month[key][category] += max(0.0, consumption)
            series = {
                name: [by_month[key][name] for key in month_keys]
                for name in ("Газ", "Электроэнергия", "Вода")
            }
            self.dashboard_chart.set_data(month_names, series)
            if hasattr(self, "analytics_forecast_chart"):
                self.analytics_forecast_chart.set_data(month_names, series)
                
            self.dashboard_chart_title.setText(
                f"Динамика потребления ресурсов ({month_names[0]} — {month_names[-1]} {month_keys[-1][0]})"
            )

            target_year, target_month = latest.year, latest.month
            month_readings = [
                reading for reading, dt in parsed
                if dt.year == target_year and dt.month == target_month
            ]
            self.dashboard_payment_title.setText(
                f"К оплате за {self._month_title(target_year, target_month)}"
            )
            all_charges, due_charges, mode = self._charges_for_month(
                property_id, target_year, target_month, month_readings
            )
            print("CHARGES:", all_charges, "MODE:", mode)
            print("READINGS:", month_readings)
            due_total = sum(due_charges.values())
            if mode == "actual":
                self.dashboard_payment_value.setText(self._money(due_total))
                self.dashboard_payment_value.setToolTip("Сумма по сохранённым начислениям SQLite; учитываются только неоплаченные начисления.")
            elif mode == "estimate":
                self.dashboard_payment_value.setText("≈ " + self._money(due_total))
                self.dashboard_payment_value.setToolTip("Оценка по фактическому расходу и тарифам этого адреса. Сумма не является официальной квитанцией.")
            elif mode == "no_tariffs":
                self.dashboard_payment_value.setText("Нет тарифов")
                self.dashboard_payment_value.setToolTip("Добавьте действующие тарифы для выбранного адреса.")
            elif mode == "need_previous":
                self.dashboard_payment_value.setText("Нужны показания")
                self.dashboard_payment_value.setToolTip("Для расчёта нужны предыдущее и текущее показания за период.")
            elif mode == "missing_tariff":
                self.dashboard_payment_value.setText("Проверьте тарифы")
                self.dashboard_payment_value.setToolTip("Не найден тариф для одного из ресурсов; неполная сумма не показывается.")
            elif mode == "unavailable":
                self.dashboard_payment_value.setText("Нет расчёта")
            else:
                self.dashboard_payment_value.setText("Нет начислений")
                self.dashboard_payment_value.setToolTip("Для этого периода пока нет сохранённых начислений или достаточных данных для оценки.")
            self._set_analytics_charges(all_charges, mode)
            self._refresh_forecast_text(month_names, series)
        else:
            self.dashboard_payment_title.setText("К оплате")
            self.dashboard_payment_value.setText("Нет показаний")
            self.dashboard_payment_value.setToolTip("Сначала внесите показания счётчиков.")
            self.dashboard_chart_title.setText("Динамика потребления ресурсов")
            self.dashboard_chart.set_data([], empty_series)
            if hasattr(self, "analytics_forecast_chart"):
                self.analytics_forecast_chart.set_data([], empty_series)
            self._refresh_forecast_text([], empty_series)
            self._set_analytics_charges({"Газ": 0.0, "Вода": 0.0, "Электроэнергия": 0.0}, "no_data")

        budget_key = f"dashboard/budget/{self.user_id}/{self.current_property_id}"
        saved_budget = self.user_settings.value(budget_key, None)
        if saved_budget in (None, ""):
            self.dashboard_budget_value.setText("Не задан")
            self.dashboard_budget_button.setText("Задать бюджет")
        else:
            try:
                self.dashboard_budget_value.setText(self._money(float(saved_budget)))
                self.dashboard_budget_button.setText("Изменить бюджет")
            except (TypeError, ValueError):
                self.dashboard_budget_value.setText("Не задан")
                self.dashboard_budget_button.setText("Задать бюджет")

        today = datetime.now().date()
        if not meters:
            self.dashboard_control_value.setText("Счётчики не добавлены")
            self.dashboard_control_value.setStyleSheet("color: #6b7280; font-size: 17px; font-weight: 700;")
        else:
            expired = False
            missing_date = False
            inactive = False
            for meter in meters:
                raw_date = str(meter.get("verification_date") or "")[:10]
                try:
                    verify_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    missing_date = True
                    continue
                if verify_date < today:
                    expired = True
                if str(meter.get("status") or "Активен").casefold() not in {"активен", "active", "действует"}:
                    inactive = True
            if expired:
                self.dashboard_control_value.setText("Нужна поверка")
                self.dashboard_control_value.setStyleSheet("color: #ff4b4b; font-size: 17px; font-weight: 700;")
            elif inactive:
                self.dashboard_control_value.setText("Проверьте счётчики")
                self.dashboard_control_value.setStyleSheet("color: #ff4b4b; font-size: 17px; font-weight: 700;")
            elif missing_date:
                self.dashboard_control_value.setText("Укажите даты поверки")
                self.dashboard_control_value.setStyleSheet("color: #b7791f; font-size: 17px; font-weight: 700;")
            else:
                self.dashboard_control_value.setText("Счётчики проверены")
                self.dashboard_control_value.setStyleSheet("color: #00b979; font-size: 17px; font-weight: 700;")

    def _set_analytics_charges(self, charges: dict[str, float], mode: str) -> None:
        """Refresh the analytics donut/legend without demo figures."""
        if hasattr(self, "analytics_donut"):
            self.analytics_donut.set_data(charges if mode in {"actual", "estimate"} else {})
        labels = getattr(self, "analytics_legend", {})
        total = sum(charges.values()) if mode in {"actual", "estimate"} else 0.0
        for name, (amount_label, percent_label) in labels.items():
            value = float(charges.get(name, 0.0)) if total > 0 else 0.0
            amount_text = self._money(value) if mode in {"actual", "estimate"} else "Нет данных"
            if mode == "estimate" and total > 0:
                amount_text = "≈ " + amount_text
            amount_label.setText(f"{name} — {amount_text}")
            percent_label.setText(f"{value / total * 100:.0f}%" if total > 0 else "—")

    def _refresh_forecast_text(
        self, months: list[str], series: dict[str, list[float]]
    ) -> None:
        label = getattr(self, "analytics_forecast_text", None)
        if label is None:
            return
        if len(months) < 2:
            label.setText("Недостаточно исторических данных для сравнения месяцев.")
            return
        comparisons = []
        for name, values in series.items():
            if len(values) >= 2 and values[-2] > 0:
                change = (values[-1] - values[-2]) / values[-2] * 100
                comparisons.append((abs(change), name, change))
        if not comparisons:
            label.setText("Для сравнения нужны два последовательных ненулевых показания по ресурсу.")
            return
        _, name, change = max(comparisons)
        trend = "увеличилось" if change >= 0 else "уменьшилось"
        label.setText(
            f"По сохранённым показаниям потребление ресурса «{name}» {trend} на {abs(change):.1f}% по сравнению с предыдущим месяцем. Это сравнение, а не гарантированный прогноз."
        )

    def _meters_page(self) -> QWidget:
        """Create the meters and history page."""
        page = QWidget()

        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 0, 24, 20)

        meters_panel = QFrame()
        meters_panel.setObjectName("whitePanel")

        meters_layout = QVBoxLayout(meters_panel)
        meters_layout.setContentsMargins(20, 18, 20, 18)

        meters_header = QHBoxLayout()
        meters_title = QLabel("Приборы учета")
        meters_title.setStyleSheet("font-size: 17px; font-weight: 700;")
        add_meter_button = QPushButton("+ Добавить прибор учета")
        add_meter_button.setObjectName("primaryButton")
        add_meter_button.clicked.connect(self._open_meter_dialog)
        meters_header.addWidget(meters_title)
        meters_header.addStretch()
        meters_header.addWidget(add_meter_button)
        meters_layout.addLayout(meters_header)

        cards_layout = QHBoxLayout()
        self.meter_cards_layout = cards_layout
        meters_layout.addLayout(cards_layout)

        outer.addWidget(meters_panel)

        history_panel = QFrame()
        history_panel.setObjectName("whitePanel")

        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(20, 20, 20, 10)

        title = QLabel("История показаний и расчетов")
        title.setStyleSheet(
            "font-size: 17px; font-weight: 700;"
        )

        history_layout.addWidget(title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            [
                "Дата внесения",
                "Прибор учета",
                "Показания",
                "Расход",
                "Сумма",
                "Статус",
            ]
        )

        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.history_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        history_layout.addWidget(self.history_table)

        # ===============================
        # ПАГИНАЦИЯ ИСТОРИИ
        # ===============================

        pagination_layout = QHBoxLayout()

        self.history_prev_button = QPushButton("←")
        self.history_next_button = QPushButton("→")

        self.history_page_label = QLabel("Страница 1 из 1")
        self.history_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.history_prev_button.clicked.connect(self._history_prev_page)
        self.history_next_button.clicked.connect(self._history_next_page)

        pagination_layout.addWidget(self.history_prev_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.history_page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.history_next_button)

        history_layout.addLayout(pagination_layout)

        outer.addWidget(history_panel, 1)

        return page

    def _meter_card(
        self,
        resource: str,
        serial: str,
        verification: str,
    ) -> QFrame:
        """Create a meter summary card."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)

        resource_label = QLabel(resource)
        resource_label.setStyleSheet(
            "font-size: 15px; font-weight: 700;"
        )

        serial_label = QLabel(f"СН: {serial}")
        serial_label.setStyleSheet(
            "color: #61718f; font-weight: 600;"
        )

        verification_label = QLabel(
            f"Поверка: {verification or 'не указана'}"
        )
        verification_label.setStyleSheet(
            "color: #00b979; font-weight: 700;"
        )

        layout.addWidget(resource_label)
        layout.addWidget(serial_label)
        layout.addWidget(verification_label)

        return card

    def _open_meter_dialog(self) -> None:
        """Add a meter to the currently selected property."""
        if self.current_property_id is None:
            QMessageBox.warning(
                self, "Нет адреса", "Сначала добавьте или выберите адрес."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить прибор учета")
        dialog.resize(420, 280)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        meter_type = QComboBox()
        meter_type.addItems([
            "Холодная вода", "Горячая вода", "Электричество", "Газ"
        ])
        serial_input = QLineEdit()
        serial_input.setPlaceholderText("Серийный номер")
        verification_input = QLineEdit()
        verification_input.setPlaceholderText("ГГГГ-ММ-ДД")

        form.addRow("Тип прибора:", meter_type)
        form.addRow("Серийный номер:", serial_input)
        form.addRow("Дата поверки:", verification_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.rejected.connect(dialog.reject)

        def save_meter() -> None:
            serial = serial_input.text().strip()
            if not serial:
                QMessageBox.warning(dialog, "Нет номера", "Введите серийный номер.")
                return
            try:
                create_meter_for_user(
                    meter_type.currentText(),
                    serial,
                    verification_input.text().strip(),
                    int(self.current_property_id),
                    self.user_id,
                )
                dialog.accept()
                self._load_meters()
            except Exception as error:
                QMessageBox.warning(dialog, "Ошибка сохранения", str(error))

        buttons.accepted.connect(save_meter)
        layout.addWidget(buttons)
        dialog.exec()

    def _load_meters(self) -> None:
        """Refresh meter cards and reading history for the selected address."""
        if self.current_property_id is None:
            meters = []
        else:
            meters = list_meters_for_user(self.current_property_id, self.user_id)

        while self.meter_cards_layout.count():
            item = self.meter_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        resource_names = {
            "Холодная вода": "Холодное водоснабжение (ХВС)",
            "Горячая вода": "Горячее водоснабжение (ГВС)",
            "Электричество": "Электроэнергия",
            "Электроэнергия": "Электроэнергия",
            "Газ": "Газ",
        }

        if not meters:
            empty_label = QLabel("Для выбранного адреса пока нет приборов учета.")
            empty_label.setStyleSheet("color: #6b7280; padding: 18px;")
            self.meter_cards_layout.addWidget(empty_label)
        else:
            for meter in meters:
                meter_type = meter.get("meter_type", "Прибор учета")
                self.meter_cards_layout.addWidget(
                    self._meter_card(
                        resource_names.get(meter_type, meter_type),
                        str(meter.get("serial_number", "")),
                        str(meter.get("verification_date") or ""),
                    )
                )

        self.meter_cards_layout.addStretch()
        self._load_history()
        self._refresh_dashboard()

    def _history_prev_page(self):
        if self.history_page > 1:
            self.history_page -= 1
            self._refresh_history_table()


    def _history_next_page(self):
        total_pages = max(
            1,
            (len(self.history_rows) + self.history_page_size - 1)
            // self.history_page_size
        )

        if self.history_page < total_pages:
            self.history_page += 1
            self._refresh_history_table()

    def _load_history(self) -> None:
        """Load meter history into the table."""
        readings = (
            list_readings_for_user(self.current_property_id, self.user_id)
            if self.current_property_id is not None else []
        )

        # сохраняем историю для пагинации
        self.history_rows = readings

        # начинаем с первой страницы при обновлении
        self.history_page = 1

        self._refresh_history_table()

    
    def _refresh_history_table(self) -> None:
        """Refresh history table with correct columns and pill-shaped status badges."""
        if not hasattr(self, "history_rows") or not self.history_rows:
            self.history_table.setRowCount(0)
            return

        page_size = 10
        total_items = len(self.history_rows)
        total_pages = max(1, (total_items + page_size - 1) // page_size)

        if not hasattr(self, "history_page") or self.history_page < 1:
            self.history_page = 1
        elif self.history_page > total_pages:
            self.history_page = total_pages

        start_idx = (self.history_page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = self.history_rows[start_idx:end_idx]

        self.history_table.setRowCount(0)

        for i, reading in enumerate(page_items):
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            resource = reading["meter_type"]
            value = reading["reading_value"]
            consumption = reading["consumption"]
            amount = float(consumption or 0) * 4.20
            
            # Статус для строки (чередуем для демонстрации или берем реальный)
            status = "Оплачено" if row % 2 == 0 else "Долг"

            # Колонки (0: Дата, 1: Прибор, 2: Показания, 3: Расход, 4: Сумма)
            values = [
                str(reading["reading_date"])[:10],
                resource,
                f"{value:g}",
                f"{consumption or 0:g}",
                f"{amount:.2f} ₽",
            ]

            # 1. Заполняем текстовые ячейки с 0 по 4 колонку
            for column, value_text in enumerate(values):
                item = QTableWidgetItem(value_text)
                self.history_table.setItem(row, column, item)

            # 2. Создаем капсулу для 5-й колонки («Статус»)
            # 2. Создаем капсулу для колонки статуса с полным заполнением ячейки
            status_container = QWidget()
            status_container.setStyleSheet("background: transparent;")
            
            status_layout = QHBoxLayout(status_container)
            # Убираем лишние отступы контейнера, чтобы капсула занимала всю ячейку
            status_layout.setContentsMargins(4, 2, 4, 2)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if status == "Оплачено":
                status_label.setStyleSheet(
                    """
                    QLabel {
                        background-color: #d5e8d4;
                        color: #274e13;
                        border-radius: 12px;
                        padding: 6px 20px;
                        font-weight: 600;
                        font-size: 12px;
                    }
                    """
                )
            else:
                status_label.setStyleSheet(
                    """
                    QLabel {
                        background-color: #f8cecc;
                        color: #b85450;
                        border-radius: 12px;
                        padding: 6px 20px;
                        font-weight: 600;
                        font-size: 12px;
                    }
                    """
                )

            # Растягиваем капсулу по горизонтали на всю ширину ячейки
            status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            
            status_layout.addWidget(status_label)
            self.history_table.setCellWidget(row, 5, status_container)

        if hasattr(self, "history_page_label"):
            self.history_page_label.setText(
                f"Страница {self.history_page} из {total_pages}"
            )
    
            

    def _analytics_page(self) -> QWidget:
        """Create the analytics and forecasts page."""
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 0, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Аналитика и прогнозы")
        title.setObjectName("pageTitle")

        layout.addWidget(title)

        # =====================================================
        # РАСПРЕДЕЛЕНИЕ ЗАТРАТ
        # =====================================================

        distribution_panel = QFrame()
        distribution_panel.setObjectName("whitePanel")

        distribution_layout = QVBoxLayout(
            distribution_panel
        )
        distribution_layout.setContentsMargins(
            24,
            20,
            24,
            20,
        )
        distribution_layout.setSpacing(18)

        distribution_title = QLabel(
            "Распределение затрат за текущий месяц"
        )

        distribution_title.setStyleSheet(
            "font-size: 18px; font-weight: 700;"
        )

        distribution_layout.addWidget(
            distribution_title
        )

        distribution_content = QHBoxLayout()
        distribution_content.setSpacing(30)

        # Круговая диаграмма

        donut = DonutChart()
        self.analytics_donut = donut

        donut.setMinimumSize(
            300,
            235,
        )

        distribution_content.addWidget(
            donut,
            1,
        )

        # Легенда

        legend = QVBoxLayout()
        legend.setSpacing(18)

        legend.addStretch()

        legend_items = [
            ("Газ", "Нет данных", "—", "#718096"),
            ("Вода", "Нет данных", "—", "#2955d9"),
            ("Электроэнергия", "Нет данных", "—", "#ffc400"),
        ]
        self.analytics_legend = {}

        for name, amount, percent, color in legend_items:
            row = QHBoxLayout()
            row.setSpacing(10)

            color_label = QLabel()
            color_label.setFixedSize(
                22,
                22,
            )

            color_label.setStyleSheet(
                f"""
                background: {color};
                border-radius: 11px;
                """
            )

            resource_label = QLabel(
                f"{name} — {amount}"
            )

            resource_label.setStyleSheet(
                """
                font-size: 15px;
                font-weight: 600;
                """
            )

            percent_label = QLabel(
                percent
            )
            self.analytics_legend[name] = (resource_label, percent_label)

            percent_label.setStyleSheet(
                """
                color: #6b7280;
                font-size: 14px;
                font-weight: 700;
                """
            )

            row.addWidget(
                color_label
            )

            row.addWidget(
                resource_label
            )

            row.addStretch()

            row.addWidget(
                percent_label
            )

            legend.addLayout(row)

        legend.addStretch()

        distribution_content.addLayout(
            legend,
            1,
        )

        distribution_layout.addLayout(
            distribution_content
        )

        layout.addWidget(
            distribution_panel,
            1,
        )

        # =====================================================
        # ПРОГНОЗ ПОТРЕБЛЕНИЯ
        # =====================================================

        forecast_panel = QFrame()
        forecast_panel.setObjectName(
            "whitePanel"
        )

        forecast_layout = QVBoxLayout(
            forecast_panel
        )

        forecast_layout.setContentsMargins(
            24,
            20,
            24,
            20,
        )

        forecast_layout.setSpacing(14)

        forecast_title = QLabel(
            "Прогноз потребления ресурсов"
        )

        forecast_title.setStyleSheet(
            """
            font-size: 18px;
            font-weight: 700;
            """
        )

        forecast_layout.addWidget(
            forecast_title
        )

        forecast_text = QLabel(
            "Загрузка истории показаний…"
        )
        self.analytics_forecast_text = forecast_text
        forecast_text.setWordWrap(True)

        forecast_text.setStyleSheet(
            """
            color: #6b7280;
            font-size: 14px;
            """
        )

        forecast_layout.addWidget(
            forecast_text
        )

        # График динамики

        forecast_chart = ResourceBars()
        self.analytics_forecast_chart = forecast_chart

        forecast_chart.setMinimumHeight(
            205
        )

        forecast_layout.addWidget(
            forecast_chart
        )

        # =====================================================
        # АНОМАЛИЯ
        # =====================================================

        anomaly = QFrame()
        self.analytics_anomaly_frame = anomaly  # <--- СОХРАНЯЕМ ССЫЛКУ ДЛЯ УПРАВЛЕНИЯ

        # По умолчанию скрываем блок, пока не проверим данные
        anomaly.hide()

        anomaly.setStyleSheet(
            """
            QFrame {
                background: #fff0f0;
                border-radius: 6px;
            }
            """
        )

        anomaly_layout = QVBoxLayout(
            anomaly
        )

        anomaly_layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )

        anomaly_title = QLabel(
            "⚠  Обнаружена аномалия в потреблении!"
        )

        anomaly_title.setStyleSheet(
            """
            color: #ff4b4b;
            font-weight: 700;
            font-size: 15px;
            """
        )

        anomaly_text = QLabel(
            "Расход по прибору ХВС превышает "
            "среднюю норму на 28%. "
            "Рекомендуем проверить трубы "
            "на наличие скрытых утечек."
        )

        anomaly_text.setWordWrap(True)

        anomaly_text.setStyleSheet(
            """
            color: #374151;
            font-size: 14px;
            """
        )

        anomaly_layout.addWidget(
            anomaly_title
        )

        anomaly_layout.addWidget(
            anomaly_text
        )

        forecast_layout.addWidget(
            anomaly
        )

        layout.addWidget(
            forecast_panel,
            1,
        )

        return page

    def _reports_page(self) -> QWidget:
        """Build the report page in the three-column Figma layout."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(8, 0, 24, 20)
        outer.setSpacing(14)

        panel = QFrame()
        panel.setObjectName("whitePanel")
        panel.setMinimumHeight(285)
        grid = QGridLayout(panel)
        grid.setContentsMargins(24, 22, 24, 24)
        grid.setHorizontalSpacing(34)
        grid.setVerticalSpacing(18)
        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 4)

        def section_title(text: str) -> QLabel:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet(
                "font-size: 17px; font-weight: 700; color: #111827;"
            )
            return label

        grid.addWidget(section_title("Формирование нового отчёта"), 0, 0)
        grid.addWidget(section_title("Выбрать ресурсы для отчёта"), 0, 1)
        grid.addWidget(section_title("Доступные форматы для скачивания"), 0, 2)

        # Period and property controls.
        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 8, 0, 0)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.report_period_combo = QComboBox()
        self.report_period_combo.setMinimumWidth(200)
        self.report_period_combo.setMinimumHeight(36)

        self.report_property_combo = QComboBox()
        self.report_property_combo.setMinimumWidth(250)
        self.report_property_combo.setMinimumHeight(36)
        try:
            properties = list_properties_for_user(self.user_id)
            for prop in properties:
                self.report_property_combo.addItem(
                    str(prop.get("address", "Адрес без названия")),
                    int(prop["id"]),
                )
        except Exception as error:
            QMessageBox.warning(self, "Не удалось загрузить адреса", str(error))

        if self.report_property_combo.count() == 0:
            self.report_property_combo.addItem("Адреса не добавлены", None)
            self.report_property_combo.setEnabled(False)

        top_id = getattr(self, "current_property_id", None)
        if top_id is None and hasattr(self, "address_combo"):
            top_id = self.address_combo.currentData()
        if top_id is not None:
            selected_index = self.report_property_combo.findData(int(top_id))
            if selected_index >= 0:
                self.report_property_combo.setCurrentIndex(selected_index)

        form.addRow("Период:", self.report_period_combo)
        form.addRow("Объект:", self.report_property_combo)
        grid.addWidget(form_host, 1, 0)

        self.report_resource_checks: dict[str, QCheckBox] = {}
        resources_host = QWidget()
        resources_layout = QVBoxLayout(resources_host)
        resources_layout.setContentsMargins(0, 8, 0, 0)
        resources_layout.setSpacing(9)
        for resource in ("Вода", "Электричество", "Газ"):
            checkbox = QCheckBox(resource)
            checkbox.setChecked(True)
            self.report_resource_checks[resource] = checkbox
            resources_layout.addWidget(checkbox)
        resources_layout.addStretch(1)
        grid.addWidget(resources_host, 1, 1)

        downloads_host = QWidget()
        downloads_layout = QVBoxLayout(downloads_host)
        downloads_layout.setContentsMargins(0, 8, 0, 0)
        downloads_layout.setSpacing(12)

        pdf_button = FormatDownloadButton(
            "Скачать квитанцию за период (.pdf)",
            "PDF",
            "#ef4444",
        )
        pdf_button.setToolTip("Сохранить квитанцию в формате PDF")
        pdf_button.clicked.connect(self._generate_receipt_pdf)

        excel_button = FormatDownloadButton(
            "Экспортировать журнал начислений (.xlsx)",
            "XLSX",
            "#10b981",
        )
        excel_button.setToolTip("Сохранить журнал начислений в формате Excel")
        excel_button.clicked.connect(self._export_charges_xlsx)

        downloads_layout.addWidget(pdf_button)
        downloads_layout.addWidget(excel_button)
        downloads_layout.addStretch(1)
        grid.addWidget(downloads_host, 1, 2)

        summary_button = QPushButton("Сформировать сводку")
        summary_button.setObjectName("primaryButton")
        summary_button.setMinimumSize(235, 40)
        summary_button.clicked.connect(self._form_report_summary)
        grid.addWidget(
            summary_button,
            2,
            0,
            1,
            2,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        note = QLabel(
            "Суммы в отчёте рассчитаны по демонстрационному тарифу "
            "4,20 ₽ за единицу. Подключите реальные тарифы для точных начислений."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6b7280; font-size: 12px; padding-top: 2px;")
        grid.addWidget(note, 3, 0, 1, 3)

        outer.addWidget(panel)
        outer.addStretch(1)

        self.report_property_combo.currentIndexChanged.connect(
            self._refresh_report_periods
        )
        self._refresh_report_periods()
        return page

    @staticmethod
    def _report_resource_matches(meter_type: str, selected: list[str]) -> bool:
        """Return whether a meter belongs to any selected report resource."""
        name = (meter_type or "").strip().casefold()
        aliases = {
            "Вода": ("вод", "хвс", "гвс"),
            "Электричество": ("электр", "electric"),
            "Газ": ("газ", "gas"),
        }
        return any(
            token in name
            for category in selected
            for token in aliases.get(category, ())
        )

    def _refresh_report_periods(self, *_args) -> None:
        """Populate month choices based on the selected property's data."""
        if not hasattr(self, "report_period_combo"):
            return

        property_id = self.report_property_combo.currentData()
        reading_dates: list[datetime] = []
        if property_id is not None:
            try:
                for row in list_readings_for_user(int(property_id), self.user_id):
                    raw_date = str(row.get("reading_date", ""))[:10]
                    try:
                        reading_dates.append(datetime.strptime(raw_date, "%Y-%m-%d"))
                    except ValueError:
                        continue
            except Exception as error:
                QMessageBox.warning(self, "Ошибка загрузки показаний", str(error))

        base = max(reading_dates) if reading_dates else datetime.now()
        month_start = base.replace(day=1)
        month_names = (
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        )
        self.report_period_combo.blockSignals(True)
        self.report_period_combo.clear()
        cursor = month_start
        for _ in range(18):
            key = cursor.strftime("%Y-%m")
            label = f"{month_names[cursor.month - 1]} {cursor.year}"
            self.report_period_combo.addItem(label, key)
            previous_day = cursor - timedelta(days=1)
            cursor = previous_day.replace(day=1)
        self.report_period_combo.blockSignals(False)
        self.report_period_combo.setCurrentIndex(0 if self.report_period_combo.count() else -1)

    @staticmethod
    def _consumption_limits(meter_type: str) -> tuple[float, float]:
        """Return (warning threshold, hard limit) for one reading interval.

        These are protective demo thresholds, not official utility standards.
        They are intentionally generous and can be adjusted for a specific
        property or meter model later.
        """
        name = (meter_type or "").casefold()
        if any(token in name for token in ("вод", "хвс", "гвс")):
            return 100.0, 1000.0
        if any(token in name for token in ("электр", "electric")):
            return 10_000.0, 100_000.0
        if any(token in name for token in ("газ", "gas")):
            return 1_000.0, 10_000.0
        return 10_000.0, 100_000.0

    def _update_reading_value_in_database(
        self,
        source: dict,
        corrected_value: float,
        corrected_consumption: float,
    ) -> None:
        """Update an existing reading through the project's SQLite connection.

        Column/table names are discovered from SQLite metadata so this works
        with the project schema's common naming variants (ReadingID/reading_id,
        Value/reading_value, MeterID/meter_id).
        """
        from app.database.connection import get_connection

        reading_id = source.get("id")
        meter_id = source.get("meter_id")
        if reading_id is None or meter_id is None:
            raise RuntimeError(
                "У записи отсутствует ID показания или ID счётчика; "
                "безопасно обновить её автоматически нельзя."
            )

        connection = get_connection()
        cursor = connection.cursor()
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        def normalize(identifier: str) -> str:
            return "".join(character for character in identifier.casefold() if character.isalnum())

        def quote(identifier: str) -> str:
            return '"' + identifier.replace('"', '""') + '"'

        for table_row in tables:
            table_name = str(table_row[0])
            table_literal = quote(table_name)
            columns_info = cursor.execute(
                f"PRAGMA table_info({table_literal})"
            ).fetchall()
            column_names = [str(column[1]) for column in columns_info]
            by_normalized = {normalize(name): name for name in column_names}

            id_column = next(
                (by_normalized[key] for key in ("readingid", "reading_id", "id") if key in by_normalized),
                None,
            )
            value_column = next(
                (by_normalized[key] for key in ("readingvalue", "value") if key in by_normalized),
                None,
            )
            meter_column = next(
                (by_normalized[key] for key in ("meterid", "meter_id") if key in by_normalized),
                None,
            )
            if not (id_column and value_column and meter_column):
                continue

            assignments = [f"{quote(value_column)} = ?"]
            values: list[float | int] = [float(corrected_value)]
            consumption_column = by_normalized.get("consumption")
            if consumption_column:
                assignments.append(f"{quote(consumption_column)} = ?")
                values.append(float(corrected_consumption))

            values.extend([int(reading_id), int(meter_id)])
            sql = (
                f"UPDATE {table_literal} SET {', '.join(assignments)} "
                f"WHERE {quote(id_column)} = ? AND {quote(meter_column)} = ?"
            )
            cursor.execute(sql, values)
            if cursor.rowcount > 0:
                connection.commit()
                return

        raise RuntimeError(
            "Не удалось найти запись показания в SQLite. "
            "Проверьте схему таблицы Readings в app/database/connection.py."
        )

    def _repair_anomalous_report_reading(
        self,
        source: dict,
        meter_type: str,
        previous_value: float,
        current_value: float,
        consumption: float,
        hard_limit: float,
    ) -> bool:
        """Offer to correct a clearly implausible stored meter reading."""
        raw_value, accepted = QInputDialog.getText(
            self,
            "Подозрительное показание",
            (
                f"Найдено подозрительное показание прибора «{meter_type}».\n"
                f"Предыдущее: {previous_value:g}\n"
                f"Сохранено: {current_value:g}\n"
                f"Расход: {consumption:,.2f}\n\n"
                "Введите правильное текущее показание с самого счётчика.\n"
                "Не вводите примерное значение. Если не уверены, нажмите «Отмена»."
            ).replace(",", " "),
            QLineEdit.EchoMode.Normal,
            "",
        )
        if not accepted:
            return False

        try:
            corrected_value = float(raw_value.strip().replace(" ", "").replace(",", "."))
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Некорректное значение", "Введите число, например 357,0.")
            return False
        if not math.isfinite(corrected_value) or corrected_value < 0:
            QMessageBox.warning(self, "Некорректное значение", "Показание должно быть неотрицательным конечным числом.")
            return False
        if corrected_value < previous_value:
            QMessageBox.warning(
                self,
                "Показание меньше предыдущего",
                f"Новое значение ({corrected_value:g}) меньше предыдущего ({previous_value:g}). Проверьте цифры и разрядность.",
            )
            return False

        corrected_consumption = corrected_value - previous_value
        if corrected_consumption > hard_limit:
            QMessageBox.warning(
                self,
                "Расход всё ещё слишком велик",
                f"Получился расход {corrected_consumption:,.2f}. Для прибора «{meter_type}» это превышает защитный предел {hard_limit:,.0f}. Запись не изменена.".replace(",", " "),
            )
            return False

        warning_limit, _ = self._consumption_limits(meter_type)
        if corrected_consumption > warning_limit:
            answer = QMessageBox.question(
                self,
                "Проверьте расход",
                f"После исправления расход составит {corrected_consumption:.2f}. Вы уверены, что переписали значение правильно?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False

        try:
            self._update_reading_value_in_database(
                source,
                corrected_value,
                corrected_consumption,
            )
        except Exception as error:
            QMessageBox.warning(self, "Не удалось исправить показание", str(error))
            return False

        QMessageBox.information(
            self,
            "Показание исправлено",
            "Запись обновлена в базе данных. Отчёт будет пересчитан по исправленному значению.",
        )
        if hasattr(self, "history_table"):
            try:
                self._load_meters()
            except Exception:
                pass
        return True

    def _get_report_payload(self, show_message: bool = True):
        """Return selected property, month and filtered readings for exports."""
        property_id = self.report_property_combo.currentData()
        period_key = self.report_period_combo.currentData()
        selected_resources = [
            name for name, checkbox in self.report_resource_checks.items()
            if checkbox.isChecked()
        ]
        if property_id is None:
            if show_message:
                QMessageBox.warning(self, "Не выбран адрес", "Добавьте или выберите адрес недвижимости.")
            return None
        if not selected_resources:
            if show_message:
                QMessageBox.warning(self, "Не выбраны ресурсы", "Отметьте хотя бы один ресурс для отчёта.")
            return None

        address = self.report_property_combo.currentText()
        try:
            source_rows = list_readings_for_user(int(property_id), self.user_id)
        except Exception as error:
            if show_message:
                QMessageBox.warning(self, "Ошибка чтения данных", str(error))
            return None

        rows = []
        for source in source_rows:
            if str(source.get("reading_date", ""))[:7] != str(period_key):
                continue
            meter_type = str(source.get("meter_type", "Прибор учёта"))
            if not self._report_resource_matches(meter_type, selected_resources):
                continue

            try:
                current_value = float(source.get("reading_value") or 0)
            except (TypeError, ValueError):
                current_value = 0.0
            previous_raw = source.get("previous_value")
            try:
                previous_value = float(previous_raw) if previous_raw not in (None, "") else None
            except (TypeError, ValueError):
                previous_value = None

            try:
                stored_consumption = float(source.get("consumption") or 0)
            except (TypeError, ValueError):
                stored_consumption = 0.0

            if previous_value is not None:
                consumption = current_value - previous_value
                warning_limit, hard_limit = self._consumption_limits(meter_type)
                if consumption < 0 or consumption > hard_limit:
                    if self._repair_anomalous_report_reading(
                        source,
                        meter_type,
                        previous_value,
                        current_value,
                        consumption,
                        hard_limit,
                    ):
                        # Reload from SQLite to ensure exports use corrected data.
                        return self._get_report_payload(show_message=show_message)
                    return None
            else:
                # A first reading has no known baseline; use the service's
                # calculated consumption (normally zero) rather than treating
                # the entire meter value as monthly usage.
                consumption = stored_consumption

            tariff = 4.20  # Existing demo rate used by the history page.
            rows.append({
                "date": str(source.get("reading_date", ""))[:10],
                "resource": meter_type,
                "serial": str(source.get("serial_number", "")),
                "previous": previous_value,
                "current": current_value,
                "consumption": consumption,
                "tariff": tariff,
                "amount": consumption * tariff,
            })

        rows.sort(key=lambda item: (item["date"], item["resource"], item["serial"]))
        if not rows:
            if show_message:
                period_label = self.report_period_combo.currentText()
                QMessageBox.information(
                    self,
                    "Нет данных за период",
                    f"Для адреса «{address}» нет показаний за период «{period_label}» "
                    "по выбранным ресурсам. Выберите другой период или ресурсы.",
                )
            return None

        return {
            "property_id": int(property_id),
            "address": address,
            "period_key": str(period_key),
            "period_label": self.report_period_combo.currentText(),
            "rows": rows,
            "total_consumption": sum(row["consumption"] for row in rows),
            "total_amount": sum(row["amount"] for row in rows),
        }

    def _form_report_summary(self) -> None:
        """Show a summary of the currently selected reporting data."""
        payload = self._get_report_payload()
        if payload is None:
            return
        QMessageBox.information(
            self,
            "Сводка за период",
            f"Адрес: {payload['address']}\n"
            f"Период: {payload['period_label']}\n"
            f"Записей: {len(payload['rows'])}\n"
            f"Суммарный расход: {payload['total_consumption']:.2f}\n"
            f"Расчётная сумма: {payload['total_amount']:.2f} ₽\n\n"
            "Использован демонстрационный тариф 4,20 ₽ за единицу.",
        )

    def _generate_receipt_pdf(self) -> None:
        """Save a period receipt to PDF using Qt's built-in PDF painter."""
        payload = self._get_report_payload()
        if payload is None:
            return

        suggested_name = f"Квитанция_{payload['period_key']}_{payload['property_id']}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить квитанцию в PDF",
            suggested_name,
            "PDF-файлы (*.pdf)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        try:
            writer = QPdfWriter(file_path)
            writer.setTitle(f"Квитанция за {payload['period_label']}")
            writer.setCreator("Мониторинг расходов ЖКХ")
            writer.setResolution(96)
            writer.setPageLayout(QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(14, 14, 14, 14),
                QPageLayout.Unit.Millimeter,
            ))
            painter = QPainter(writer)
            if not painter.isActive():
                raise RuntimeError("Не удалось создать PDF-файл.")

            page_width = writer.width()
            page_height = writer.height()
            margin = max(36, int(page_width * 0.055))
            content_width = page_width - 2 * margin
            columns = [0.12, 0.18, 0.18, 0.12, 0.12, 0.12, 0.16]
            headers = ["Дата", "Ресурс", "Серийный №", "Пред.", "Текущ.", "Расход", "Сумма, ₽"]
            col_edges = [margin]
            for fraction in columns:
                col_edges.append(col_edges[-1] + int(content_width * fraction))
            col_edges[-1] = page_width - margin

            def draw_text(x: int, y: int, width: int, height: int, text_value: str,
                          font_size: int = 9, bold: bool = False,
                          color: str = TEXT, align=None) -> None:
                painter.setPen(QColor(color))
                font = QFont("DejaVu Sans", font_size)
                font.setBold(bold)
                painter.setFont(font)
                alignment = align if align is not None else (
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                painter.drawText(QRectF(x, y, width, height), alignment, text_value)

            def draw_document_heading(continuation: bool = False) -> int:
                y = 35
                title = "КВИТАНЦИЯ ЗА КОММУНАЛЬНЫЕ УСЛУГИ"
                if continuation:
                    title += " (продолжение)"
                draw_text(margin, y, content_width, 32, title, 15, True, NAVY,
                          Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                y += 39
                draw_text(margin, y, content_width, 22, f"Период: {payload['period_label']}", 10, True)
                y += 22
                draw_text(margin, y, content_width, 30, f"Адрес: {payload['address']}", 10)
                y += 26
                draw_text(margin, y, content_width, 22, "Журнал показаний и расчётных начислений", 10, True)
                return y + 8

            def draw_table_header(y: int) -> int:
                painter.fillRect(QRectF(margin, y, content_width, 28), QColor(NAVY))
                painter.setPen(QPen(QColor("#d9e2f2"), 1))
                painter.drawRect(QRectF(margin, y, content_width, 28))
                for idx, title in enumerate(headers):
                    x1, x2 = col_edges[idx], col_edges[idx + 1]
                    draw_text(x1 + 3, y + 1, max(1, x2 - x1 - 6), 26, title,
                              7, True, WHITE,
                              Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                return y + 28

            y = draw_table_header(draw_document_heading())
            row_height = 25
            for index, row in enumerate(payload["rows"]):
                if y + row_height + 90 > page_height:
                    writer.newPage()
                    y = draw_table_header(draw_document_heading(continuation=True))
                if index % 2:
                    painter.fillRect(QRectF(margin, y, content_width, row_height), QColor("#f5f7fb"))
                painter.setPen(QPen(QColor("#d9dee8"), 1))
                painter.drawRect(QRectF(margin, y, content_width, row_height))
                values = [
                    row["date"], row["resource"], row["serial"],
                    "—" if row["previous"] is None else f"{row['previous']:g}",
                    f"{row['current']:g}", f"{row['consumption']:.2f}",
                    f"{row['amount']:.2f}",
                ]
                for idx, value in enumerate(values):
                    x1, x2 = col_edges[idx], col_edges[idx + 1]
                    draw_text(x1 + 3, y + 1, max(1, x2 - x1 - 6), row_height - 2,
                              str(value), 7 if idx in (1, 2) else 8, False, TEXT)
                for x in col_edges[1:-1]:
                    painter.setPen(QPen(QColor("#d9dee8"), 1))
                    painter.drawLine(x, y, x, y + row_height)
                y += row_height

            if y + 75 > page_height:
                writer.newPage()
                y = draw_document_heading(continuation=True)
            y += 10
            painter.setPen(QPen(QColor(NAVY), 2))
            painter.drawLine(margin, y, page_width - margin, y)
            y += 8
            draw_text(margin, y, content_width, 22,
                      f"Всего записей: {len(payload['rows'])}", 9, True)
            y += 23
            draw_text(margin, y, content_width, 22,
                      f"Общий расход: {payload['total_consumption']:.2f}", 9, True)
            y += 23
            draw_text(margin, y, content_width, 24,
                      f"Итого к оплате (расчётно): {payload['total_amount']:.2f} ₽",
                      11, True, NAVY)
            y += 28
            draw_text(margin, y, content_width, 34,
                      "Примечание: сумма рассчитана по демонстрационному тарифу "
                      "4,20 ₽ за единицу. Это не официальный платёжный документ.",
                      8, False, MUTED)
            painter.end()
        except Exception as error:
            QMessageBox.warning(self, "Не удалось сохранить PDF", str(error))
            return

        QMessageBox.information(self, "PDF готов", f"Квитанция сохранена:\n{file_path}")

    def _export_charges_xlsx(self) -> None:
        """Export the selected period's charge journal to a dependency-free XLSX file."""
        payload = self._get_report_payload()
        if payload is None:
            return
        suggested_name = f"Журнал_начислений_{payload['period_key']}_{payload['property_id']}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт журнала начислений",
            suggested_name,
            "Книга Excel (*.xlsx)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"
        try:
            self._write_xlsx_journal(file_path, payload)
        except Exception as error:
            QMessageBox.warning(self, "Не удалось экспортировать Excel", str(error))
            return
        QMessageBox.information(self, "Экспорт завершён", f"Журнал сохранён:\n{file_path}")

    def _write_xlsx_journal(self, file_path: str, payload: dict) -> None:
        """Write a small, styled OOXML workbook using only the Python standard library."""
        rows = payload["rows"]
        last_data_row = 4 + len(rows)
        total_row = 5 + len(rows)
        address = str(payload["address"])
        period_label = str(payload["period_label"])
        period_key = str(payload["period_key"])
        tariff_note = "Демонстрационный тариф: 4,20 ₽ за единицу. Для реальных начислений подключите тарифы."

        def inline_cell(ref: str, value, style: int = 0) -> str:
            value_text = xml_escape(str(value), quote=True)
            style_attr = f' s="{style}"' if style else ""
            return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t xml:space="preserve">{value_text}</t></is></c>'

        def number_cell(ref: str, value: float, style: int = 4) -> str:
            style_attr = f' s="{style}"' if style else ""
            return f'<c r="{ref}"{style_attr}><v>{float(value):.10g}</v></c>'

        def formula_cell(ref: str, formula: str, cached_value: float, style: int = 5) -> str:
            return f'<c r="{ref}" s="{style}"><f>{xml_escape(formula)}</f><v>{float(cached_value):.10g}</v></c>'

        columns = [
            ("A", 14), ("B", 38), ("C", 22), ("D", 18), ("E", 15),
            ("F", 15), ("G", 15), ("H", 17), ("I", 18),
        ]
        sheet_rows: list[str] = []
        sheet_rows.append(
            '<row r="1" ht="30" customHeight="1">'
            + inline_cell("A1", "Журнал начислений ЖКХ", 1)
            + "</row>"
        )
        sheet_rows.append(
            '<row r="2" ht="24" customHeight="1">'
            + inline_cell("A2", f"Адрес: {address} | Период: {period_label}", 2)
            + "</row>"
        )
        sheet_rows.append(
            '<row r="3" ht="28" customHeight="1">'
            + inline_cell("A3", tariff_note, 2)
            + "</row>"
        )
        headers = [
            "Дата", "Адрес", "Ресурс", "Серийный номер", "Предыдущие показания",
            "Текущие показания", "Расход", "Тариф, ₽/ед.", "Начислено, ₽",
        ]
        sheet_rows.append(
            '<row r="4" ht="34" customHeight="1">'
            + "".join(inline_cell(f"{col}4", value, 3) for (col, _), value in zip(columns, headers))
            + "</row>"
        )

        for idx, entry in enumerate(rows, start=5):
            cells = [
                inline_cell(f"A{idx}", entry["date"], 6),
                inline_cell(f"B{idx}", address, 6),
                inline_cell(f"C{idx}", entry["resource"], 6),
                inline_cell(f"D{idx}", entry["serial"], 6),
                (number_cell(f"E{idx}", entry["previous"], 4) if entry["previous"] is not None else f'<c r="E{idx}" s="4"/>'),
                number_cell(f"F{idx}", entry["current"], 4),
                number_cell(f"G{idx}", entry["consumption"], 4),
                number_cell(f"H{idx}", entry["tariff"], 5),
                formula_cell(f"I{idx}", f"G{idx}*H{idx}", entry["amount"], 5),
            ]
            sheet_rows.append(f'<row r="{idx}">' + "".join(cells) + "</row>")

        first_data = 5
        last_data = last_data_row
        sheet_rows.append(
            f'<row r="{total_row}" ht="24" customHeight="1">'
            + inline_cell(f"A{total_row}", "ИТОГО", 7)
            + f'<c r="G{total_row}" s="8"><f>SUM(G{first_data}:G{last_data})</f><v>{payload["total_consumption"]:.10g}</v></c>'
            + f'<c r="I{total_row}" s="9"><f>SUM(I{first_data}:I{last_data})</f><v>{payload["total_amount"]:.10g}</v></c>'
            + "</row>"
        )

        col_xml = "".join(
            f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>'
            for i, (_, width) in enumerate(columns, start=1)
        )
        worksheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<dimension ref="A1:I{total_row}"/>'
            '<sheetViews><sheetView workbookViewId="0" showGridLines="0">'
            '<pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
            '<sheetFormatPr defaultRowHeight="20"/>'
            f'<cols>{col_xml}</cols><sheetData>{"".join(sheet_rows)}</sheetData>'
            '<mergeCells count="3"><mergeCell ref="A1:I1"/><mergeCell ref="A2:I2"/><mergeCell ref="A3:I3"/></mergeCells>'
            f'<autoFilter ref="A4:I{last_data}"/>'
            '<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
            '</worksheet>'
        )

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>'
        )
        package_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )
        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Журнал начислений" sheetId="1" r:id="rId1"/></sheets>'
            '<calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>'
            '</workbook>'
        )
        workbook_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="2"><numFmt numFmtId="164" formatCode="0.00"/>'
            '<numFmt numFmtId="165" formatCode="#,##0.00 &quot;₽&quot;"/></numFmts>'
            '<fonts count="3">'
            '<font><sz val="11"/><name val="Arial"/></font>'
            '<font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Arial"/></font>'
            '<font><b/><color rgb="FF203F91"/><sz val="16"/><name val="Arial"/></font>'
            '</fonts>'
            '<fills count="4"><fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FF203F91"/><bgColor indexed="64"/></patternFill></fill>'
            '<fill><patternFill patternType="solid"><fgColor rgb="FFF9DDDD"/><bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
            '<border><left style="thin"><color rgb="FFD9DEE8"/></left><right style="thin"><color rgb="FFD9DEE8"/></right>'
            '<top style="thin"><color rgb="FFD9DEE8"/></top><bottom style="thin"><color rgb="FFD9DEE8"/></bottom><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="10">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="center"/></xf>'
            '<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
            '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
            '<xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right" vertical="center"/></xf>'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
            '<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>'
            '<xf numFmtId="164" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyNumberFormat="1"><alignment horizontal="right" vertical="center"/></xf>'
            '<xf numFmtId="165" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyNumberFormat="1"><alignment horizontal="right" vertical="center"/></xf>'
            '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>'
            '</styleSheet>'
        )

        with ZipFile(file_path, "w", compression=ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", content_types)
            workbook.writestr("_rels/.rels", package_rels)
            workbook.writestr("xl/workbook.xml", workbook_xml)
            workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            workbook.writestr("xl/styles.xml", styles_xml)
            workbook.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    def _settings_page(self) -> QWidget:
        """Create the settings page with functional sections."""
        page = QWidget()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 0, 24, 30)
        layout.setSpacing(12)

        title = QLabel("Настройки")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Профиль, безопасность, жильё, уведомления и банковские карты"
        )
        subtitle.setStyleSheet("color: #6b7280;")
        layout.addWidget(subtitle)

        settings = [
            ("profile", "Профиль и аккаунт", "Изменение имени, телефона и email",
             self._profile_dialog),
            ("security", "Безопасность", "Пароль, 2FA и подключённые устройства",
             self._security_dialog),
            ("property", "Выбор жилья", "Адреса объектов недвижимости и основной объект",
             self._property_dialog),
            ("notifications", "Настройка уведомлений", "Каналы и типы уведомлений",
             self._notification_dialog),
            ("bank", "Банковские карты", "Добавление, просмотр и удаление карт",
             self._bank_cards_dialog),
        ]

        for icon_kind, title_text, description, callback in settings:
            card = QFrame()
            card.setObjectName("whitePanel")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(18, 14, 18, 14)
            card_layout.setSpacing(16)

            icon_label = SettingsIcon(icon_kind)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(3)
            name_label = QLabel(title_text)
            name_label.setStyleSheet(
                "font-size: 16px; font-weight: 700;"
            )
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #6b7280;")
            text_layout.addWidget(name_label)
            text_layout.addWidget(desc_label)

            button = QPushButton("Открыть")
            button.setObjectName("primaryButton")
            button.setFixedWidth(110)
            button.clicked.connect(callback)

            card_layout.addWidget(icon_label)
            card_layout.addLayout(text_layout, 1)
            card_layout.addWidget(button)
            layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(container)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _open_settings_form(
        self,
        title: str,
        fields: list[tuple[str, str]],
    ) -> None:
        """Open a reusable settings dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(500, 320)

        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        inputs: list[QLineEdit] = []

        for label, value in fields:
            field = QLineEdit(value)
            form.addRow(label, field)
            inputs.append(field)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _settings_dialog_title(self, icon_kind: str, text: str) -> QWidget:
        """Build a dialog title with the same colorful icon as settings cards."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 8)
        row_layout.setSpacing(10)
        row_layout.addWidget(SettingsIcon(icon_kind))
        label = QLabel(text)
        label.setStyleSheet("font-size: 18px; font-weight: 700;")
        row_layout.addWidget(label, 1)
        return row

    def _profile_dialog(self) -> None:
        """Open functional profile settings."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Профиль и аккаунт")
        dialog.resize(520, 330)

        layout = QVBoxLayout(dialog)
        layout.addWidget(self._settings_dialog_title("profile", "Профиль и аккаунт"))

        db_name = getattr(self, 'user_name', "Демо-пользователь")
        db_phone = ""
        db_email = ""

        # Загружаем актуальные данные и проверяем колонку телефона
        try:
            with get_connection() as connection:
                cursor = connection.cursor()
                if hasattr(self, 'user_id') and self.user_id:
                    columns_info = cursor.execute("PRAGMA table_info(AppUsers)").fetchall()
                    column_names = [str(col[1]).casefold() for col in columns_info]
                    
                    phone_col = next((col for col in column_names if "phone" in col), None)
                    if not phone_col:
                        cursor.execute("ALTER TABLE AppUsers ADD COLUMN Phone TEXT DEFAULT ''")
                        connection.commit()
                        phone_col = "phone"

                    query = f"SELECT FullName, Email, {phone_col} FROM AppUsers WHERE UserID = ?"
                    row = cursor.execute(query, (self.user_id,)).fetchone()
                    
                    if row:
                        db_name = row[0] if row[0] else db_name
                        db_email = row[1] if row[1] else ""
                        db_phone = row[2] if row[2] else ""
        except Exception:
            pass

        form = QFormLayout()
        name_input = QLineEdit(db_name)
        phone_input = QLineEdit(db_phone)
        email_input = QLineEdit(db_email)
        
        form.addRow("ФИО пользователя:", name_input)
        form.addRow("Телефон:", phone_input)
        form.addRow("Email:", email_input)
        layout.addLayout(form)

        save = QPushButton("Сохранить изменения")
        save.setObjectName("primaryButton")
        layout.addWidget(save)

        def save_profile() -> None:
            new_name = name_input.text().strip()
            new_phone = phone_input.text().strip()
            new_email = email_input.text().strip().lower()

            if not new_name or not new_email:
                QMessageBox.warning(
                    dialog,
                    "Ошибка",
                    "ФИО и Email не могут быть пустыми.",
                )
                return

            try:
                with get_connection() as connection:
                    cursor = connection.cursor()
                    
                    if not hasattr(self, 'user_id') or not self.user_id:
                        raise ValueError("Не определен ID текущего пользователя.")

                    columns_info = cursor.execute("PRAGMA table_info(AppUsers)").fetchall()
                    column_names = [str(col[1]).casefold() for col in columns_info]
                    phone_col = next((col for col in column_names if "phone" in col), "Phone")

                    cursor.execute(
                        f"UPDATE AppUsers SET FullName = ?, Email = ?, {phone_col} = ? WHERE UserID = ?",
                        (new_name, new_email, new_phone, self.user_id)
                    )

                    if cursor.rowcount == 0:
                        raise RuntimeError("Не удалось найти пользователя в базе данных для сохранения.")

                    connection.commit()

                # Обновляем имя в памяти приложения
                self.user_name = new_name

                # Если в главном окне есть метод или ссылка на виджет отображения имени (например, self.user_name_label), обновим его сразу:
                if hasattr(self, 'user_name_label') and self.user_name_label:
                    self.user_name_label.setText(new_name)
                elif hasattr(self, 'update_sidebar_user_info'):
                    self.update_sidebar_user_info()

                QMessageBox.information(
                    dialog,
                    "Успех",
                    "Изменения профиля успешно сохранены!",
                )
                dialog.accept()
            except Exception as error:
                QMessageBox.warning(
                    dialog,
                    "Ошибка базы данных",
                    f"Не удалось сохранить данные:\n{error}",
                )

        save.clicked.connect(save_profile)
        dialog.exec()
    def _security_dialog(self) -> None:
        """Show security settings and real information about this computer."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Безопасность")
        dialog.resize(600, 560)

        layout = QVBoxLayout(dialog)
        layout.addWidget(self._settings_dialog_title("security", "Безопасность"))

        password_title = QLabel("Смена пароля")
        password_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(password_title)

        form = QFormLayout()
        old_password = QLineEdit()
        old_password.setEchoMode(QLineEdit.EchoMode.Password)
        new_password = QLineEdit()
        new_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Старый пароль:", old_password)
        form.addRow("Новый пароль:", new_password)
        layout.addLayout(form)

        change_button = QPushButton("Сменить пароль")
        change_button.setObjectName("primaryButton")
        layout.addWidget(change_button)

        status = QLabel()
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet(
            "background: #00b979; color: white; border-radius: 4px; "
            "padding: 8px;"
        )
        status.hide()
        layout.addWidget(status)

        

        # 1. Сначала получаем статус и секрет 2FA из базы данных
        try:
            is_2fa_enabled, saved_secret = get_user_2fa_info(self.user_id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Ошибка открытия безопасности",
                f"Не удалось загрузить настройки 2FA:\n{error}",
            )
            return

        # 2. Создаем чекбокс 2FA и сразу задаем ему состояние
        two_fa = QCheckBox("Включить двухфакторную аутентификацию (2FA)")
        two_fa.blockSignals(True)
        two_fa.setChecked(is_2fa_enabled)
        two_fa.blockSignals(False)
        layout.addWidget(two_fa)  # Добавляем чекбокс в интерфейс диалога

        # 3. Функция смены пароля с проверкой длины (от 8 до 16 символов)
        # Функция смены пароля с проверкой длины (от 8 до 16 символов) и прямым обновлением в БД
        def change_password() -> None:
            old_pass = old_password.text()
            new_pass = new_password.text()

            if not old_pass or not new_pass:
                QMessageBox.warning(
                    dialog,
                    "Ошибка",
                    "Заполните старый и новый пароль.",
                )
                return

            # Проверка длины нового пароля (от 8 до 16 символов)
            if not (8 <= len(new_pass) <= 16):
                QMessageBox.warning(
                    dialog,
                    "Некорректная длина пароля",
                    "Пароль должен содержать от 8 до 16 символов.",
                )
                return

            try:
                with get_connection() as connection:
                    cursor = connection.cursor()
                    
                    if not hasattr(self, 'user_id') or not self.user_id:
                        raise ValueError("Не определен ID текущего пользователя.")

                    # Проверяем старый пароль
                    row = cursor.execute(
                        "SELECT PasswordSalt, PasswordHash FROM AppUsers WHERE UserID = ?",
                        (self.user_id,)
                    ).fetchone()
                    
                    if row:
                        salt_bytes = bytes.fromhex(str(row[0]))
                        expected_hash = str(row[1])
                        _, candidate_hash = _password_material(old_pass, salt_bytes)
                        if not hmac.compare_digest(candidate_hash, expected_hash):
                            QMessageBox.warning(
                                dialog,
                                "Ошибка",
                                "Указан неверный старый пароль.",
                            )
                            return
                    else:
                        raise ValueError(f"Пользователь с ID {self.user_id} не найден.")

                    # Генерируем новую соль и хэш для нового пароля
                    salt_hex, hash_hex = _password_material(new_pass)

                    # ПРОВЕРКА НА УНИКАЛЬНОСТЬ: проверяем, нет ли уже такого хэша у других пользователей
                    existing_hash = cursor.execute(
                        "SELECT 1 FROM AppUsers WHERE PasswordHash = ? AND UserID != ?",
                        (hash_hex, self.user_id)
                    ).fetchone()

                    if existing_hash:
                        QMessageBox.warning(
                            dialog,
                            "Пароль занят",
                            "Этот пароль уже используется другим пользователем. Выберите другую комбинацию.",
                        )
                        return

                    # Обновляем пароль, если он уникален
                    cursor.execute(
                        "UPDATE AppUsers SET PasswordSalt = ?, PasswordHash = ? WHERE UserID = ?",
                        (salt_hex, hash_hex, self.user_id)
                    )
                    
                    if cursor.rowcount == 0:
                        raise RuntimeError("Не удалось обновить пароль: запись пользователя не найдена.")

                    connection.commit()

                QMessageBox.information(
                    dialog,
                    "Успех",
                    "Пароль успешно изменен и является уникальным!",
                )
                dialog.accept()
            except Exception as error:
                QMessageBox.warning(
                    dialog,
                    "Ошибка базы данных",
                    f"Не удалось обновить пароль:\n{error}",
                )

        change_button.clicked.connect(change_password)

        # 3. Обработчик переключения
      
        def on_2fa_toggled(state_val: int) -> None:
            enabled = state_val != 0

            if enabled:
                secret = pyotp.random_base32()
                dlg = Setup2FaDialog(self.user_name, secret, self)

                if dlg.exec() != QDialog.DialogCode.Accepted:
                    two_fa.blockSignals(True)
                    two_fa.setChecked(False)
                    two_fa.blockSignals(False)
                    return

                try:
                    update_user_2fa(self.user_id, True, secret)

                    # Проверяем, что настройки действительно сохранились
                    saved_enabled, saved_secret = get_user_2fa_info(self.user_id)

                    if not saved_enabled or saved_secret != secret:
                        raise RuntimeError(
                            "Не удалось подтвердить сохранение настроек 2FA."
                        )

                    QMessageBox.information(
                        self,
                        "2FA подключена",
                        "Двухфакторная аутентификация успешно активирована."
                    )

                except Exception as error:
                    two_fa.blockSignals(True)
                    two_fa.setChecked(False)
                    two_fa.blockSignals(False)

                    QMessageBox.critical(
                        self,
                        "Ошибка настройки 2FA",
                        f"Не удалось сохранить настройки:\n{error}"
                    )

            else:
                try:
                    update_user_2fa(self.user_id, False, "")

                    saved_enabled, _ = get_user_2fa_info(self.user_id)

                    if saved_enabled:
                        raise RuntimeError(
                            "Не удалось подтвердить отключение 2FA."
                        )

                    QMessageBox.information(
                        self,
                        "2FA отключена",
                        "Двухфакторная аутентификация выключена."
                    )

                except Exception as error:
                    two_fa.blockSignals(True)
                    two_fa.setChecked(True)
                    two_fa.blockSignals(False)

                QMessageBox.critical(
                    self,
                    "Ошибка настроек 2FA",
                    f"Не удалось изменить настройки:\n{error}"
                )



        # 4. Подключаем обработчик и добавляем в layout РОВНО ОДИН РАЗ
        two_fa.stateChanged.connect(on_2fa_toggled)
        two_fa.setToolTip("Защита аккаунта с помощью одноразовых кодов TOTP.")
        layout.addWidget(two_fa)

        devices_title = QLabel("Информация о текущем устройстве")
        devices_title.setStyleSheet("font-weight: 700; padding-top: 8px;")
        layout.addWidget(devices_title)

        # Это текущее рабочее устройство PySide6
        try:
            device_name = socket.gethostname() or "Неизвестное устройство"
        except OSError:
            device_name = "Не удалось определить имя устройства"

        os_name = f"{platform.system()} {platform.release()}".strip()
        if not os_name:
            os_name = platform.platform() or "Не удалось определить ОС"

        try:
            os_user = getpass.getuser() or "не определён"
        except (ImportError, OSError):
            os_user = "не определён"

        local_ip = "не определён"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as ip_socket:
                ip_socket.connect(("8.8.8.8", 80))
                local_ip = ip_socket.getsockname()[0]
        except OSError:
            pass

        active_time = datetime.now().astimezone().strftime("%d.%m.%Y, %H:%M:%S")
        devices = QListWidget()
        devices.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        devices.setMinimumHeight(130)
        devices.addItem(
            "Текущее устройство · Активно сейчас\n"
            f"Имя устройства: {device_name}\n"
            f"Операционная система: {os_name}\n"
            f"Пользователь ОС: {os_user}\n"
            f"Локальный IP-адрес: {local_ip}\n"
            f"Время проверки: {active_time}"
        )
        devices.setCurrentRow(0)
        layout.addWidget(devices, 1)

        terminate_all = QPushButton("Завершить все другие процессы")
        terminate_all.setObjectName("primaryButton")
        def terminate_devices() -> None:
            QMessageBox.information(
                dialog,
                "Другие устройства",
                "Сейчас приложение показывает реальную информацию только о текущем компьютере. "
                "Удалённых сеансов в локальной демонстрационной версии нет. "
                "Чтобы отображать и завершать входы с других устройств, нужно подключить "
                "серверную авторизацию и журнал сеансов.",
            )

        terminate_all.clicked.connect(terminate_devices)
        layout.addWidget(terminate_all)
        dialog.exec()

    def _property_dialog(self) -> None:
        """Choose an address and add one when the service supports it."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Выбор жилья")
        dialog.resize(650, 400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(self._settings_dialog_title("property", "Выбор жилья"))
        layout.addWidget(QLabel("Выберите объект:"))

        properties_widget = QListWidget()

        def fill_properties() -> None:
            properties_widget.clear()
            for prop in list_properties_for_user(self.user_id):
                item = QListWidgetItem(str(prop["address"]))
                item.setData(Qt.ItemDataRole.UserRole, int(prop["id"]))
                properties_widget.addItem(item)
            current_id = self.current_property_id
            for row in range(properties_widget.count()):
                item = properties_widget.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == current_id:
                    properties_widget.setCurrentItem(item)
                    break

        fill_properties()
        layout.addWidget(properties_widget)

        buttons_row = QHBoxLayout()
        select_button = QPushButton("Выбрать адрес")
        add_button = QPushButton("+ Добавить новый адрес")
        add_button.setObjectName("primaryButton")
        buttons_row.addWidget(select_button)
        buttons_row.addWidget(add_button)
        layout.addLayout(buttons_row)

        def select_property() -> None:
            item = properties_widget.currentItem()
            if item is None:
                QMessageBox.warning(dialog, "Адрес не выбран", "Выберите адрес из списка.")
                return
            property_id = int(item.data(Qt.ItemDataRole.UserRole))
            index = self.address_combo.findData(property_id)
            if index >= 0:
                self.address_combo.setCurrentIndex(index)
            dialog.accept()

        def add_property() -> None:
            address, ok = self._text_input(
                dialog, "Новый адрес", "Введите полный адрес:"
            )
            if not ok or not address.strip():
                return
            try:
                created_id = create_property_for_user(address.strip(), self.user_id)
                self._reload_property_selector(int(created_id))
                fill_properties()
            except Exception as error:
                QMessageBox.warning(dialog, "Ошибка добавления адреса", str(error))

        select_button.clicked.connect(select_property)
        properties_widget.itemDoubleClicked.connect(lambda _item: select_property())
        add_button.clicked.connect(add_property)
        dialog.exec()

    def _text_input(
        self, parent: QWidget, title: str, label: str
    ) -> tuple[str, bool]:
        """Small text input dialog used by settings."""
        dialog = QDialog(parent)
        dialog.setWindowTitle(title)
        dialog.resize(420, 160)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(label))
        field = QLineEdit()
        layout.addWidget(field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return field.text().strip(), accepted

    def _notification_dialog(self) -> None:
        """Open functional notification settings."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка уведомлений")
        dialog.resize(560, 430)

        layout = QVBoxLayout(dialog)
        layout.addWidget(self._settings_dialog_title("notifications", "Настройка уведомлений"))
        layout.addWidget(QLabel("Выберите какие уведомления хотите получать:"))

        channels = QFrame()
        channels.setObjectName("whitePanel")
        channel_layout = QVBoxLayout(channels)
        channel_layout.addWidget(QLabel("Способ получения уведомлений"))

        channel_checks = []
        for text, checked in [
            ("Push — получать уведомления на устройство", True),
            ("Email — получать уведомления на электронную почту", True),
            ("SMS — получать важные уведомления по SMS", False),
        ]:
            check = QCheckBox(text)
            check.setChecked(checked)
            channel_checks.append(check)
            channel_layout.addWidget(check)

        layout.addWidget(channels)

        types = QFrame()
        types.setObjectName("whitePanel")
        type_layout = QVBoxLayout(types)
        type_layout.addWidget(QLabel("Типы уведомлений"))

        for text, checked in [
            ("Платежи — напоминания об оплате", True),
            ("Показания приборов — напоминания о передаче показаний", True),
            ("Задолженность — информация о задолженности", True),
            ("Новости и предложения — информационные сообщения", False),
        ]:
            check = QCheckBox(text)
            check.setChecked(checked)
            type_layout.addWidget(check)

        layout.addWidget(types)

        save = QPushButton("Сохранить")
        save.setObjectName("primaryButton")
        save.clicked.connect(dialog.accept)
        layout.addWidget(save)
        dialog.exec()

    def _bank_cards_dialog(self) -> None:
        """Show and manage linked bank cards."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Банковские карты")
        dialog.resize(780, 560)

        root = QVBoxLayout(dialog)
        root.addWidget(self._settings_dialog_title("bank", "Банковские карты"))

        cards_layout = QHBoxLayout()
        cards_container = QWidget()
        cards_box = QVBoxLayout(cards_container)
        cards_box.setSpacing(12)
        cards_layout.addWidget(cards_container, 1)

        form_panel = QFrame()
        form_panel.setStyleSheet(
            "QFrame { background: #00b979; border-radius: 5px; }"
            "QLabel { color: white; }"
            "QLineEdit { background: white; }"
        )
        form = QVBoxLayout(form_panel)
        form.addWidget(QLabel("Добавить банковскую карту"))

        number = QLineEdit()
        number.setPlaceholderText("0000 0000 0000 0000")
        expiry = QLineEdit()
        expiry.setPlaceholderText("00/00")
        cvv = QLineEdit()
        cvv.setPlaceholderText("000")
        bank = QLineEdit()
        bank.setPlaceholderText("Название банка")

        form.addWidget(QLabel("Номер карты"))
        form.addWidget(number)
        form.addWidget(QLabel("Срок действия"))
        form.addWidget(expiry)
        form.addWidget(QLabel("CVV"))
        form.addWidget(cvv)
        form.addWidget(QLabel("Банк"))
        form.addWidget(bank)

        add_button = QPushButton("Добавить")
        add_button.setObjectName("primaryButton")
        form.addWidget(add_button)
        form.addStretch()
        cards_layout.addWidget(form_panel, 1)

        root.addLayout(cards_layout)

        def render_cards() -> None:
            while cards_box.count():
                item = cards_box.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            if not self.bank_cards:
                empty = QLabel("Банковских карт пока нет.")
                empty.setStyleSheet("color: #6b7280; padding: 20px;")
                cards_box.addWidget(empty)
                return

            for index, card in enumerate(self.bank_cards):
                card_frame = QFrame()
                card_frame.setStyleSheet(
                    "QFrame { background: #147de2; color: white; "
                    "border-radius: 6px; }"
                    "QLabel { color: white; }"
                )
                card_layout = QVBoxLayout(card_frame)
                top = QHBoxLayout()
                bank_label = QLabel(str(card["bank"]))
                bank_label.setStyleSheet(
                    "font-size: 15px; font-weight: 700;"
                )
                main_label = QLabel("✓ Основная" if card["main"] else "")
                top.addWidget(bank_label)
                top.addStretch()
                top.addWidget(main_label)
                card_layout.addLayout(top)
                card_layout.addWidget(QLabel(str(card["number"])))
                card_layout.addWidget(QLabel(str(card["expiry"])))

                delete = QPushButton("Удалить")
                delete.setStyleSheet(
                    "background: #ff4b4b; color: white; "
                    "border-radius: 4px; padding: 7px 14px;"
                )
                delete.clicked.connect(
                    lambda checked=False, i=index: self._delete_bank_card(
                        i, dialog, render_cards
                    )
                )
                card_layout.addWidget(
                    delete, alignment=Qt.AlignmentFlag.AlignRight
                )
                cards_box.addWidget(card_frame)

            cards_box.addStretch()

        def add_card() -> None:
            card_number = number.text().strip()
            card_expiry = expiry.text().strip()
            card_bank = bank.text().strip() or "Банк"

            if not card_number or not card_expiry:
                QMessageBox.warning(
                    dialog, "Ошибка",
                    "Введите номер карты и срок действия."
                )
                return

            self.bank_cards.append(
                {
                    "bank": card_bank,
                    "number": card_number,
                    "expiry": card_expiry,
                    "main": not bool(self.bank_cards),
                }
            )
            number.clear()
            expiry.clear()
            cvv.clear()
            bank.clear()
            render_cards()

        add_button.clicked.connect(add_card)
        render_cards()
        dialog.exec()

    def _delete_bank_card(
        self,
        index: int,
        dialog: QDialog,
        refresh_callback,
    ) -> None:
        """Confirm and delete a bank card, then show a 5-second toast."""
        if index < 0 or index >= len(self.bank_cards):
            return

        card = self.bank_cards[index]
        confirm = QMessageBox(dialog)
        confirm.setWindowTitle("Удалить банковскую карту?")
        confirm.setText(
            f'{card["bank"]}\n**** {str(card["number"])[-4:]}'
        )
        confirm.setInformativeText(
            "После удаления карта больше не будет использоваться для оплаты."
        )
        cancel_button = confirm.addButton(
            "Отмена", QMessageBox.ButtonRole.RejectRole
        )
        delete_button = confirm.addButton(
            "Удалить", QMessageBox.ButtonRole.DestructiveRole
        )
        confirm.setDefaultButton(delete_button)
        confirm.exec()

        if confirm.clickedButton() is not delete_button:
            return

        was_main = bool(card["main"])
        self.bank_cards.pop(index)

        if was_main and self.bank_cards:
            self.bank_cards[0]["main"] = True

        refresh_callback()
        self._show_toast("Банковская карта удалена")

    def _show_toast(self, message: str) -> None:
        """Show a temporary notification for exactly five seconds."""
        toast = QLabel(message, self)
        toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toast.setStyleSheet(
            "background: #dbe2f0; color: #111827; "
            "border-radius: 6px; padding: 12px 22px; "
            "font-weight: 700;"
        )
        toast.adjustSize()
        x = max(20, self.width() - toast.width() - 40)
        y = max(80, self.height() - toast.height() - 45)
        toast.move(x, y)
        toast.raise_()
        toast.show()
        QTimer.singleShot(5000, toast.deleteLater)

    def _open_reading_dialog(self) -> None:
        """Open the meter reading dialog."""

        print("ОТКРЫТИЕ ОКНА ПОКАЗАНИЙ")

        meters = list_meters_for_user(
            self.current_property_id, self.user_id
        )

        print("ПОЛУЧЕННЫЕ ПРИБОРЫ:", meters)

        for m in meters:
            print(dict(m))



        print("АДРЕС:", self.current_property_id)
        print("ПРИБОРЫ:", meters)
        

        dialog = QDialog(self)
        dialog.setWindowTitle("Внести показания")
        dialog.resize(420, 260)

        layout = QVBoxLayout(dialog)

        title = QLabel("Новое показание")
        title.setStyleSheet(
            "font-size: 19px; font-weight: 700;"
        )

        layout.addWidget(title)

        form = QFormLayout()

        meter_combo = QComboBox()

        for meter in meters:
            meter_combo.addItem(
                f"{meter['meter_type']} ({meter['serial_number']})",
                int(meter["id"])
    )
    
        reading_input = QLineEdit()
        reading_input.setPlaceholderText(
            "Введите новое показание"
        )

        form.addRow("Прибор учета:", meter_combo)
        form.addRow("Показания:", reading_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.rejected.connect(dialog.reject)

        def save_reading() -> None:
            """Validate the entered reading before saving it to SQLite."""
            meter_id = meter_combo.currentData()

            if meter_id is None:
                QMessageBox.warning(
                    dialog,
                    "Ошибка",
                    "Сначала добавьте прибор учёта.",
                )
                return

            raw_value = reading_input.text().strip().replace(" ", "").replace(",", ".")
            try:
                new_value = float(raw_value)
            except (TypeError, ValueError):
                QMessageBox.warning(dialog, "Некорректное значение", "Введите числовое показание, например 357,0.")
                return
            if not math.isfinite(new_value) or new_value < 0:
                QMessageBox.warning(dialog, "Некорректное значение", "Показание должно быть неотрицательным конечным числом.")
                return

            selected_meter = next(
                (meter for meter in meters if int(meter.get("id", -1)) == int(meter_id)),
                None,
            )
            meter_type = str((selected_meter or {}).get("meter_type", meter_combo.currentText()))

            try:
                existing_rows = list_readings_for_user(int(self.current_property_id), self.user_id) if self.current_property_id is not None else []
                same_meter_rows = [
                    row for row in existing_rows
                    if str(row.get("meter_id")) == str(meter_id)
                    and row.get("reading_value") not in (None, "")
                ]
                previous_value = None
                if same_meter_rows:
                    last_row = max(
                        same_meter_rows,
                        key=lambda row: (str(row.get("reading_date", "")), int(row.get("id") or 0)),
                    )
                    previous_value = float(last_row.get("reading_value") or 0)

                if previous_value is not None:
                    if new_value < previous_value:
                        QMessageBox.warning(
                            dialog,
                            "Показание меньше предыдущего",
                            f"Введено {new_value:g}, а последнее сохранённое показание — {previous_value:g}.\n\nПроверьте цифры и разрядность. Новая запись не сохранена.",
                        )
                        return

                    consumption_delta = new_value - previous_value
                    warning_limit, hard_limit = self._consumption_limits(meter_type)
                    if consumption_delta > hard_limit:
                        QMessageBox.warning(
                            dialog,
                            "Слишком большой расход",
                            f"Получился расход {consumption_delta:,.2f} за интервал, что превышает защитный предел {hard_limit:,.0f} для прибора «{meter_type}».\n\nПоказание не сохранено. Проверьте, не добавлен ли лишний ноль. Если в базе уже есть ошибочная запись, исправьте её через экспорт отчёта.".replace(",", " "),
                        )
                        return
                    if consumption_delta > warning_limit:
                        answer = QMessageBox.question(
                            dialog,
                            "Проверьте показание",
                            f"Расход составит {consumption_delta:.2f}, это необычно много для прибора «{meter_type}».\n\nВы уверены, что переписали показание правильно?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No,
                        )
                        if answer != QMessageBox.StandardButton.Yes:
                            return

                consumption = create_reading_for_user(int(meter_id), str(new_value), self.user_id)
                dialog.accept()
                self._load_meters()
                QMessageBox.information(
                    self,
                    "Показания",
                    "Показание успешно сохранено.\n\n" + f"Расход: {float(consumption):.2f}",
                )

            except Exception as error:
                QMessageBox.warning(dialog, "Ошибка", str(error))

        buttons.accepted.connect(save_reading)

        layout.addWidget(buttons)

        dialog.exec()

    def closeEvent(self, event) -> None:
        """Handle application close."""
        event.accept()

class Setup2FaDialog(QDialog):
    """Диалог активации TOTP 2FA с показaнием QR-кода."""

    def __init__(self, user_name: str, secret: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Привязка 2FA Authenticator")
        self.setFixedSize(380, 500)
        self.secret = secret

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_label = QLabel("Отсканируйте QR-код в приложении\n(Google Authenticator, Яндекс Ключ и др.):")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 1. Формируем URI для приложения-аутентификатора
        totp = pyotp.TOTP(self.secret)
        otpauth_url = totp.provisioning_uri(name=user_name, issuer_name="ЖКХ Мониторинг")

        # 2. Рендерим QR-код
        qr_img = qrcode.make(otpauth_url)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        
        qimage = QImage()
        qimage.loadFromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimage)

        qr_label = QLabel()
        qr_label.setPixmap(pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio))
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(qr_label)

        secret_label = QLabel(f"Секретный код (ручной ввод):\n<b>{self.secret}</b>")
        secret_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        secret_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(secret_label)

        form = QFormLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("6 цифр из приложения")
        self.code_input.setMaxLength(6)
        form.addRow("Одноразовый код:", self.code_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._verify_code)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _verify_code(self) -> None:
        code = self.code_input.text().strip()

        if not code.isdigit() or len(code) != 6:
            QMessageBox.warning(
                self,
                "Ошибка проверки",
                "Введите ровно 6 цифр из приложения-аутентификатора.",
            )
            return

        totp = pyotp.TOTP(self.secret)

        if totp.verify(code, valid_window=1):
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Ошибка проверки",
                "Неверный или просроченный код. "
                "Проверьте время на телефоне и повторите попытку.",
            )

    


