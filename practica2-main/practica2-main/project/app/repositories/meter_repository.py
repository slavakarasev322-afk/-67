
"""Repository for Meters, Readings and related calculations."""

from __future__ import annotations

from datetime import date

from app.database.connection import get_connection


def get_meters() -> list[dict]:
    """Return meters with names matching the current UI."""
    with get_connection() as connection:
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
            ORDER BY m."MeterID"
            """
        ).fetchall()

    return [dict(row) for row in rows]


def add_meter(
    meter_type: str,
    serial_number: str,
    verification_date: str = "",
) -> int:
    """Create a meter linked to the first property of the user."""
    with get_connection() as connection:
        property_row = connection.execute(
            """
            SELECT "PropertyID"
            FROM "Properties"
            ORDER BY "PropertyID"
            LIMIT 1
            """
        ).fetchone()

        if property_row is None:
            raise RuntimeError(
                "Не найден объект недвижимости."
            )

        cursor = connection.execute(
            """
            INSERT INTO "Meters" (
                "SerialNo",
                "Type",
                "InstallDT",
                "VerifyDT",
                "Status",
                "PropertyID"
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                serial_number,
                meter_type,
                date.today().isoformat(),
                verification_date or None,
                "Активен",
                property_row["PropertyID"],
            ),
        )

        return int(cursor.lastrowid)


def delete_meter(meter_id: int) -> None:
    """Delete a meter and its dependent readings."""
    with get_connection() as connection:
        connection.execute(
            'DELETE FROM "Meters" WHERE "MeterID" = ?',
            (meter_id,),
        )


def add_reading(
    meter_id: int,
    value: float,
) -> float:
    """Create a reading and return consumption since the previous reading."""
    with get_connection() as connection:
        previous = connection.execute(
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
            float(previous["Value"])
            if previous is not None
            else None
        )

        if (
            previous_value is not None
            and value < previous_value
        ):
            raise ValueError(
                "Новое показание не может быть меньше предыдущего."
            )

        reading_date = date.today().isoformat()

        connection.execute(
            """
            INSERT INTO "Readings" (
                "MeterID",
                "Value",
                "ReadingDate"
            )
            VALUES (?, ?, ?)
            """,
            (
                meter_id,
                value,
                reading_date,
            ),
        )

        if previous_value is None:
            return value

        return value - previous_value


def get_readings() -> list[dict]:
    """Return reading history with calculated consumption."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                r."ReadingID" AS id,
                r."MeterID" AS meter_id,
                m."Type" AS meter_type,
                m."SerialNo" AS serial_number,
                r."Value" AS reading_value,
                r."ReadingDate" AS reading_date,
                r."PhotoPath" AS photo_path,
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
                    ORDER BY r2."ReadingDate" DESC,
                             r2."ReadingID" DESC
                    LIMIT 1
                ) AS previous_value
            FROM "Readings" AS r
            JOIN "Meters" AS m
              ON m."MeterID" = r."MeterID"
            ORDER BY r."ReadingDate" DESC,
                     r."ReadingID" DESC
            """
        ).fetchall()

    result = []

    for row in rows:
        item = dict(row)

        current = float(item["reading_value"])
        previous = item["previous_value"]

        if previous is None:
            consumption = current
        else:
            consumption = current - float(previous)

        item["consumption"] = consumption
        item["status"] = "normal"

        result.append(item)

    return result
