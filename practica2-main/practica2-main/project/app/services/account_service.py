"""SQLite-backed user accounts for the ЖКХ desktop application.

This module owns authentication records and associates each property with one
user. It deliberately uses the project's existing get_connection() factory.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import secrets
import sqlite3
from typing import Any

from app.database.connection import get_connection

_USERS_TABLE = "AppUsers"
_ITERATIONS = 200_000


def _quote(identifier: str) -> str:
    """Quote an SQLite identifier obtained from sqlite_master/PRAGMA."""
    return '"' + identifier.replace('"', '""') + '"'


def _connect() -> sqlite3.Connection:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    return conn


def _find_table(conn: sqlite3.Connection, candidates: tuple[str, ...]) -> str | None:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    by_lower = {str(row[0]).casefold(): str(row[0]) for row in tables}
    for candidate in candidates:
        if candidate.casefold() in by_lower:
            return by_lower[candidate.casefold()]
    return None


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row[1])
        for row in conn.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
    ]


def _pick(columns: list[str], *candidates: str) -> str | None:
    by_lower = {column.casefold(): column for column in columns}
    for candidate in candidates:
        found = by_lower.get(candidate.casefold())
        if found:
            return found
    return None


def _password_material(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS
    )
    return salt.hex(), digest.hex()


def initialize_auth_schema() -> None:
    """Добавляет поля 2FA в таблицу, используемую авторизацией."""
    with get_connection() as connection:
        table = _find_table(connection, (_USERS_TABLE,))

        if table is None:
            raise RuntimeError(
                f"Таблица {_USERS_TABLE} не найдена в базе данных."
            )

        columns = _column_names(connection, table)

        if not _pick(columns, "is_2fa_enabled"):
            connection.execute(
                f"ALTER TABLE {_quote(table)} "
                "ADD COLUMN is_2fa_enabled INTEGER NOT NULL DEFAULT 0"
            )

        if not _pick(columns, "totp_secret"):
            connection.execute(
                f"ALTER TABLE {_quote(table)} "
                "ADD COLUMN totp_secret TEXT NOT NULL DEFAULT ''"
            )

def _user_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    keys = set(row.keys())
    user_id_key = "UserID" if "UserID" in keys else "userid"
    login_key = "Login" if "Login" in keys else "login"
    email_key = "Email" if "Email" in keys else "email"
    name_key = "FullName" if "FullName" in keys else "fullname"
    return {
        "id": int(row[user_id_key]),
        "user_id": int(row[user_id_key]),
        "login": str(row[login_key]),
        "email": str(row[email_key]),
        "name": str(row[name_key]),
    }


def register_user(name: str, login: str, email: str, password: str) -> dict[str, Any]:
    """Create a new user in SQLite and return public account details."""
    initialize_auth_schema()
    name, login, email = name.strip(), login.strip(), email.strip().lower()
    if not all((name, login, email, password)):
        raise ValueError("Заполните все поля регистрации.")
    salt_hex, hash_hex = _password_material(password)
    conn = _connect()
    try:
        conn.execute(
            f"""INSERT INTO {_quote(_USERS_TABLE)}
                (Login, Email, FullName, PasswordSalt, PasswordHash, IsDemo)
                VALUES (?, ?, ?, ?, ?, 0)""",
            (login, email, name, salt_hex, hash_hex),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT * FROM {_quote(_USERS_TABLE)} WHERE Login = ? COLLATE NOCASE",
            (login,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Аккаунт создан, но не удалось загрузить его данные.")
        return _user_dict(row)
    except sqlite3.IntegrityError as error:
        conn.rollback()
        message = str(error).casefold()
        if "login" in message:
            raise ValueError("Такой логин уже зарегистрирован.") from error
        if "email" in message:
            raise ValueError("Этот Email уже используется.") from error
        raise ValueError("Не удалось создать аккаунт: проверьте логин и Email.") from error
    finally:
        conn.close()


def authenticate_user(login: str, password: str) -> dict[str, Any] | None:
    """Authenticate a user; return None for an invalid login/password pair."""
    initialize_auth_schema()
    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {_quote(_USERS_TABLE)} WHERE Login = ? COLLATE NOCASE",
            (login.strip(),),
        ).fetchone()
        if row is None:
            return None
        try:
            salt = bytes.fromhex(str(row["PasswordSalt"]))
            expected = str(row["PasswordHash"])
        except (KeyError, ValueError, TypeError):
            return None
        _salt_hex, candidate = _password_material(password, salt)
        if not hmac.compare_digest(candidate, expected):
            return None
        return _user_dict(row)
    finally:
        conn.close()


def import_legacy_user(user: dict[str, Any]) -> None:
    """Import an account previously stored in QSettings, if it is not in SQLite."""
    initialize_auth_schema()
    login = str(user.get("login", "")).strip()
    email = str(user.get("email", "")).strip().lower()
    name = str(user.get("name", "Пользователь")).strip()
    salt_hex = str(user.get("password_salt", "")).strip()
    hash_hex = str(user.get("password_hash", "")).strip()
    if not all((login, email, salt_hex, hash_hex)) or login.casefold() == "demo":
        return
    try:
        bytes.fromhex(salt_hex)
        bytes.fromhex(hash_hex)
    except ValueError:
        return

    conn = _connect()
    try:
        exists = conn.execute(
            f"SELECT 1 FROM {_quote(_USERS_TABLE)} WHERE Login = ? COLLATE NOCASE "
            "OR Email = ? COLLATE NOCASE",
            (login, email),
        ).fetchone()
        if exists:
            return
        conn.execute(
            f"""INSERT INTO {_quote(_USERS_TABLE)}
                (Login, Email, FullName, PasswordSalt, PasswordHash, IsDemo)
                VALUES (?, ?, ?, ?, ?, 0)""",
            (login, email, name or login, salt_hex, hash_hex),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
    finally:
        conn.close()


def get_demo_user() -> dict[str, Any]:
    account = authenticate_user("demo", "demo")
    if account is None:
        raise RuntimeError("Не удалось инициализировать демонстрационный аккаунт.")
    return account


def _properties_context(conn: sqlite3.Connection) -> tuple[str, list[str], str, str, str]:
    table = _find_table(conn, ("Properties", "properties"))
    if not table:
        raise RuntimeError("В базе не найдена таблица Properties.")
    columns = _column_names(conn, table)
    id_col = _pick(columns, "PropertyID", "property_id", "id")
    address_col = _pick(columns, "Address", "address")
    owner_col = _pick(columns, "OwnerUserID", "OwnerUserId", "UserID", "UserId")
    if not id_col or not address_col or not owner_col:
        raise RuntimeError("В таблице Properties отсутствуют поля ID, Address или OwnerUserID.")
    return table, columns, id_col, address_col, owner_col


def list_properties_for_user(user_id: int) -> list[dict[str, Any]]:
    """Return only addresses owned by this user."""
    initialize_auth_schema()
    conn = _connect()
    try:
        table, columns, id_col, address_col, owner_col = _properties_context(conn)
        type_col = _pick(columns, "Type", "PropertyType", "property_type", "type")
        area_col = _pick(columns, "Area", "area")
        residents_col = _pick(columns, "Residents", "residents")
        region_col = _pick(columns, "Region", "region")
        rows = conn.execute(
            f"SELECT * FROM {_quote(table)} WHERE {_quote(owner_col)} = ? "
            f"ORDER BY {_quote(address_col)}",
            (int(user_id),),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": int(row[id_col]),
                "address": str(row[address_col]),
                "property_type": row[type_col] if type_col else "Квартира",
                "area": row[area_col] if area_col else None,
                "residents": row[residents_col] if residents_col else None,
                "region": row[region_col] if region_col else "",
            })
        return result
    finally:
        conn.close()


def create_property_for_user(address: str, user_id: int) -> int:
    """Create a property with an explicit owner user ID."""
    initialize_auth_schema()
    address = address.strip()
    if not address:
        raise ValueError("Введите адрес объекта.")
    conn = _connect()
    try:
        table, columns, id_col, address_col, owner_col = _properties_context(conn)
        type_col = _pick(columns, "Type", "PropertyType", "property_type", "type")
        area_col = _pick(columns, "Area", "area")
        residents_col = _pick(columns, "Residents", "residents")
        region_col = _pick(columns, "Region", "region")
        created_col = _pick(columns, "CreatedAT", "CreatedAt", "created_at", "createdat")
        values: dict[str, Any] = {
            address_col: address,
            owner_col: int(user_id),
        }
        if type_col:
            values[type_col] = "Квартира"
        if area_col:
            values[area_col] = 0
        if residents_col:
            values[residents_col] = 1
        if region_col:
            values[region_col] = ""
        if created_col:
            values[created_col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Satisfy other required columns that have no default with safe empty values.
        info = conn.execute(f"PRAGMA table_info({_quote(table)})").fetchall()
        for column_info in info:
            col_name = str(column_info[1])
            not_null = int(column_info[3] or 0) == 1
            default = column_info[4]
            is_pk = int(column_info[5] or 0) > 0
            if not_null and default is None and not is_pk and col_name not in values:
                col_lower = col_name.casefold()
                if "date" in col_lower or "created" in col_lower:
                    values[col_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                elif "area" in col_lower or "count" in col_lower or "resident" in col_lower:
                    values[col_name] = 0
                else:
                    values[col_name] = ""

        col_sql = ", ".join(_quote(column) for column in values)
        placeholders = ", ".join("?" for _ in values)
        conn.execute(
            f"INSERT INTO {_quote(table)} ({col_sql}) VALUES ({placeholders})",
            tuple(values.values()),
        )
        property_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.commit()
        return property_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def assert_property_owned(property_id: int, user_id: int) -> None:
    """Raise rather than expose data when a property belongs to another user."""
    initialize_auth_schema()
    conn = _connect()
    try:
        table, _columns, id_col, _address_col, owner_col = _properties_context(conn)
        found = conn.execute(
            f"SELECT 1 FROM {_quote(table)} WHERE {_quote(id_col)} = ? "
            f"AND {_quote(owner_col)} = ?",
            (int(property_id), int(user_id)),
        ).fetchone()
        if found is None:
            raise PermissionError("Нет доступа к этому адресу. Выберите своё жильё.")
    finally:
        conn.close()


def assert_meter_owned(meter_id: int, user_id: int) -> int:
    """Validate meter ownership and return its property ID."""
    initialize_auth_schema()
    conn = _connect()
    try:
        p_table, p_cols, p_id, _p_address, owner_col = _properties_context(conn)
        m_table = _find_table(conn, ("Meters", "meters"))
        if not m_table:
            raise RuntimeError("В базе не найдена таблица Meters.")
        m_cols = _column_names(conn, m_table)
        m_id = _pick(m_cols, "MeterID", "meter_id", "id")
        m_property = _pick(m_cols, "PropertyID", "property_id")
        if not m_id or not m_property:
            raise RuntimeError("В таблице Meters отсутствуют ID или PropertyID.")
        row = conn.execute(
            f"SELECT m.{_quote(m_property)} FROM {_quote(m_table)} AS m "
            f"JOIN {_quote(p_table)} AS p ON m.{_quote(m_property)} = p.{_quote(p_id)} "
            f"WHERE m.{_quote(m_id)} = ? AND p.{_quote(owner_col)} = ?",
            (int(meter_id), int(user_id)),
        ).fetchone()
        if row is None:
            raise PermissionError("Нет доступа к этому счётчику.")
        return int(row[0])
    finally:
        conn.close()


def update_user_name(user_id: int, full_name: str) -> None:
    """Persist a user's display name in the account database."""
    initialize_auth_schema()
    full_name = full_name.strip()
    if not full_name:
        raise ValueError("Имя пользователя не может быть пустым.")
    conn = _connect()
    try:
        cursor = conn.execute(
            f"UPDATE {_quote(_USERS_TABLE)} SET FullName = ? WHERE UserID = ?",
            (full_name, int(user_id)),
        )
        if cursor.rowcount != 1:
            raise ValueError("Учётная запись не найдена.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_2fa_info(
    user_id: int | None,
) -> tuple[bool, str]:
    if user_id is None:
        return False, ""

    initialize_auth_schema()

    conn = _connect()
    try:
        row = conn.execute(
            f"""
            SELECT is_2fa_enabled, totp_secret
            FROM {_quote(_USERS_TABLE)}
            WHERE UserID = ?
            """,
            (int(user_id),),
        ).fetchone()

        if row is None:
            return False, ""

        enabled = bool(row["is_2fa_enabled"])
        secret = str(row["totp_secret"] or "")

        return enabled, secret
    finally:
        conn.close()


def update_user_2fa(
    user_id: int | None,
    enabled: bool,
    secret: str = "",
) -> None:
    if user_id is None:
        raise ValueError("Пользователь не определён.")

    initialize_auth_schema()

    conn = _connect()
    try:
        cursor = conn.execute(
            f"""
            UPDATE {_quote(_USERS_TABLE)}
            SET is_2fa_enabled = ?,
                totp_secret = ?
            WHERE UserID = ?
            """,
            (
                1 if enabled else 0,
                secret if enabled else "",
                int(user_id),
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Не удалось сохранить настройки 2FA."
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
