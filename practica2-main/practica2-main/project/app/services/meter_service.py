
"""Service layer for ЖКХ properties, meters and readings."""

from __future__ import annotations

import math
from datetime import date

from app.database.connection import get_connection


def list_properties() -> list[dict]:
    """Вернуть адреса из основной базы данных."""
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                "PropertyID" AS id,
                "Address" AS address,
                "Type" AS property_type,
                "Area" AS area,
                "Residents" AS residents,
                "Region" AS region
            FROM "Properties"
            ORDER BY "PropertyID"
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_property(
    address: str,
    property_type: str = "Квартира",
    area: float = 0.0,
    residents: int = 1,
    region: str = "",
) -> int:
    """Создать новый адрес и вернуть его ID."""
    address = address.strip()
    if not address:
        raise ValueError("Введите адрес.")

    area = float(area)
    residents = int(residents)

    if not math.isfinite(area) or area < 0:
        raise ValueError("Площадь должна быть неотрицательным числом.")
    if residents < 1:
        raise ValueError("Количество жильцов должно быть не меньше 1.")

    connection = get_connection()
    try:
        duplicate = connection.execute(
            """
            SELECT "PropertyID"
            FROM "Properties"
            WHERE LOWER(TRIM("Address")) = LOWER(TRIM(?))
            """,
            (address,),
        ).fetchone()

        if duplicate:
            raise ValueError("Такой адрес уже существует.")

        cursor = connection.execute(
            """
            INSERT INTO "Properties"
                ("Address", "Type", "Area", "Residents", "Region")
            VALUES (?, ?, ?, ?, ?)
            """,
            (address, property_type, area, residents, region.strip()),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_meters(property_id: int | None) -> list[dict]:
    """Получить счётчики только выбранного адреса."""
    if property_id is None:
        return []

    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                m."MeterID" AS id,
                m."Type" AS meter_type,
                m."SerialNo" AS serial_number,
                m."InstallDT" AS installation_date,
                m."VerifyDT" AS verification_date,
                m."Status" AS status,
                m."PropertyID" AS property_id
            FROM "Meters" AS m
            WHERE m."PropertyID" = ?
            ORDER BY m."MeterID"
            """,
            (property_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_meter(
    meter_type: str,
    serial_number: str,
    verification_date: str,
    property_id: int,
) -> int:
    """Создать счётчик, привязанный к выбранному адресу."""
    meter_type = meter_type.strip()
    serial_number = serial_number.strip()

    if not meter_type:
        raise ValueError("Выберите тип счётчика.")
    if not serial_number:
        raise ValueError("Введите серийный номер.")

    connection = get_connection()
    try:
        property_row = connection.execute(
            """
            SELECT 1
            FROM "Properties"
            WHERE "PropertyID" = ?
            """,
            (property_id,),
        ).fetchone()

        if property_row is None:
            raise ValueError("Выбранный адрес не найден.")

        cursor = connection.execute(
            """
            INSERT INTO "Meters"
                ("SerialNo", "Type", "InstallDT", "VerifyDT",
                 "Status", "PropertyID")
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                serial_number,
                meter_type,
                date.today().isoformat(),
                verification_date.strip() or None,
                "Активен",
                property_id,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def remove_meter(meter_id: int) -> None:
    """Удалить счётчик и его показания."""
    connection = get_connection()
    try:
        # Сначала удаляем показания, связанные со счётчиком.
        connection.execute(
            'DELETE FROM "Readings" WHERE "MeterID" = ?',
            (meter_id,),
        )
        connection.execute(
            'DELETE FROM "Meters" WHERE "MeterID" = ?',
            (meter_id,),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_reading(meter_id: int, value: str | float) -> float:
    """Сохранить новое показание и вернуть расход."""
    try:
        new_value = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Введите корректное число показаний.") from None

    if not math.isfinite(new_value) or new_value < 0:
        raise ValueError("Показание должно быть неотрицательным числом.")

    connection = get_connection()
    try:
        meter = connection.execute(
            'SELECT 1 FROM "Meters" WHERE "MeterID" = ?',
            (meter_id,),
        ).fetchone()

        if meter is None:
            raise ValueError("Счётчик не найден.")

        previous_row = connection.execute(
            """
            SELECT "Value"
            FROM "Readings"
            WHERE "MeterID" = ?
            ORDER BY "ReadingDate" DESC, "ReadingID" DESC
            LIMIT 1
            """,
            (meter_id,),
        ).fetchone()

        previous_value = (
            float(previous_row["Value"])
            if previous_row is not None
            else None
        )

        if previous_value is not None and new_value < previous_value:
            raise ValueError(
                f"Новое показание ({new_value:g}) меньше предыдущего "
                f"({previous_value:g})."
            )

        # Первое показание — начальная точка, расход пока равен нулю.
        consumption = (
            new_value - previous_value
            if previous_value is not None
            else 0.0
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO "Readings"
            (
                "MeterID",
                "Value",
                "ReadingDate"
            )
            VALUES (?, ?, ?)
            """,
            (
                meter_id,
                new_value,
                date.today().isoformat(),
            ),
        )


        reading_id = cursor.lastrowid

        connection.commit()

        # создаём начисление по тарифу
        from app.services.calculation_service import create_calculation

        create_calculation(
            reading_id
        )

        return consumption
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_readings(property_id: int | None) -> list[dict]:
    """Получить историю показаний выбранного адреса."""
    if property_id is None:
        return []

    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                r."ReadingID" AS id,
                r."MeterID" AS meter_id,
                r."Value" AS reading_value,
                r."ReadingDate" AS reading_date,
                m."Type" AS meter_type,
                m."SerialNo" AS serial_number,
                (
                    SELECT r2."Value"
                    FROM "Readings" AS r2
                    WHERE r2."MeterID" = r."MeterID"
                      AND (
                          r2."ReadingDate" < r."ReadingDate"
                          OR (
                              r2."ReadingDate" = r."ReadingDate"
                              AND r2."ReadingID" < r."ReadingID"
                          )
                      )
                    ORDER BY r2."ReadingDate" DESC, r2."ReadingID" DESC
                    LIMIT 1
                ) AS previous_value
            FROM "Readings" AS r
            JOIN "Meters" AS m
                ON m."MeterID" = r."MeterID"
            WHERE m."PropertyID" = ?
            ORDER BY r."ReadingDate" DESC, r."ReadingID" DESC
            """,
            (property_id,),
        ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            previous_value = item["previous_value"]
            item["consumption"] = (
                float(item["reading_value"]) - float(previous_value)
                if previous_value is not None
                else 0.0
            )
            result.append(item)

        return result
    finally:
        connection.close()