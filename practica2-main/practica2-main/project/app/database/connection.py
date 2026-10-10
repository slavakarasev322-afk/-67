"""SQLite connection and database initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config.settings import DATABASE_PATH, DATA_DIR


SCHEMA_VERSION = 2


def get_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def _table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    """Return column names for a database table."""
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def _schema_is_current(
    connection: sqlite3.Connection,
) -> bool:
    """Check whether the database matches the ER model."""
    expected = {
        "USER": {
            "UserID",
            "Email",
            "Password",
            "FullName",
            "Phone",
            "Role",
            "CreatedAT",
        },


        "BankCards": {
            "CardID",
            "UserID",
            "BankName",
            "CardNumber",
            "Expiry",
            "IsMain",
        },
        "UserPropertyRoles": {
            "UserPropertyRolesID",
            "UserID",
            "PropertyID",
            "Role",
            "GrantedAT",
        },
        "Properties": {
            "PropertyID",
            "Address",
            "Type",
            "Area",
            "Residents",
            "Region",
            "CreatedAT",
            "OwnerUserID",
        },
        "Tariffs": {
            "TariffID",
            "PropertyID",
            "ResourceType",
            "Rate",
            "ValidFrom",
            "ValidTo",
            "ZoneType",
        },
        "Meters": {
            "MeterID",
            "SerialNo",
            "Type",
            "InstallDT",
            "VerifyDT",
            "Status",
            "PropertyID",
        },
        "Readings": {
            "ReadingID",
            "MeterID",
            "Value",
            "ReadingDate",
            "PhotoPath",
            "CreatedAT",
        },
        "Calculations": {
            "CalculationID",
            "ReadingID",
            "TariffID",
            "Volume",
            "Amount",
            "PeriodStart",
            "PeriodEnd",
            "IsPaid",
            "PaidAt",
        },
        "Forecast": {
            "ForecastID",
            "MeterID",
            "Period",
            "PredictedValue",
            "PredictedAmount",
            "Confidence",
            "CreatedAT",
        },
        "Benefits": {
            "BenefitID",
            "PropertyID",
            "UserID",
            "Type",
            "Percent",
            "ValidFrom",
            "ValidTo",
        },
        "Notifications": {
            "NotificationID",
            "UserID",
            "Type",
            "Message",
            "ScheduledAT",
            "IsSent",
            "SentAT",
        },
        "AuditLog": {
            "LogID",
            "UserID",
            "Action",
            "EntityType",
            "EntityID",
            "Timestamp",
            "IpAddress",
        },
    }

    for table_name, columns in expected.items():
        if _table_columns(
            connection,
            table_name,
        ) != columns:
            return False

    return True


def _create_schema(
    connection: sqlite3.Connection,
) -> None:
    """Create all tables from the approved ER model."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS "USER" (
            "UserID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Email" TEXT NOT NULL UNIQUE,
            "Password" TEXT NOT NULL,
            "FullName" TEXT NOT NULL,
            "Phone" TEXT,
            "Role" TEXT NOT NULL DEFAULT 'Владелец',
            "CreatedAT" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS "Properties" (
            "PropertyID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Address" TEXT NOT NULL,
            "Type" TEXT NOT NULL,
            "Area" REAL NOT NULL DEFAULT 0,
            "Residents" INTEGER NOT NULL DEFAULT 1,
            "Region" TEXT,
            "CreatedAT" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS "UserPropertyRoles" (
            "UserPropertyRolesID"
                INTEGER PRIMARY KEY AUTOINCREMENT,
            "UserID" INTEGER NOT NULL,
            "PropertyID" INTEGER NOT NULL,
            "Role" TEXT NOT NULL,
            "GrantedAT" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY ("UserID")
                REFERENCES "USER" ("UserID")
                ON DELETE CASCADE,

            FOREIGN KEY ("PropertyID")
                REFERENCES "Properties" ("PropertyID")
                ON DELETE CASCADE,

            UNIQUE ("UserID", "PropertyID")
        );

        CREATE TABLE IF NOT EXISTS "Tariffs" (
            "TariffID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "PropertyID" INTEGER NOT NULL,
            "ResourceType" TEXT NOT NULL,
            "Rate" REAL NOT NULL,
            "ValidFrom" TEXT NOT NULL,
            "ValidTo" TEXT,
            "ZoneType" TEXT,

            FOREIGN KEY ("PropertyID")
                REFERENCES "Properties" ("PropertyID")
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS "Meters" (
            "MeterID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "SerialNo" TEXT NOT NULL UNIQUE,
            "Type" TEXT NOT NULL,
            "InstallDT" TEXT NOT NULL,
            "VerifyDT" TEXT,
            "Status" TEXT NOT NULL DEFAULT 'Активен',
            "PropertyID" INTEGER NOT NULL,

            FOREIGN KEY ("PropertyID")
                REFERENCES "Properties" ("PropertyID")
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS "Readings" (
            "ReadingID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "MeterID" INTEGER NOT NULL,
            "Value" REAL NOT NULL CHECK ("Value" >= 0),
            "ReadingDate" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "PhotoPath" TEXT,
            "CreatedAT" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY ("MeterID")
                REFERENCES "Meters" ("MeterID")
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS "Calculations" (
            "CalculationID"
                INTEGER PRIMARY KEY AUTOINCREMENT,

            "ReadingID" INTEGER NOT NULL,
            "TariffID" INTEGER NOT NULL,
            "Volume" REAL NOT NULL,
            "Amount" REAL NOT NULL,
            "PeriodStart" TEXT NOT NULL,
            "PeriodEnd" TEXT NOT NULL,
            "IsPaid" INTEGER NOT NULL DEFAULT 0
                CHECK ("IsPaid" IN (0, 1)),
            "PaidAt" TEXT,

            FOREIGN KEY ("ReadingID")
                REFERENCES "Readings" ("ReadingID")
                ON DELETE CASCADE,

            FOREIGN KEY ("TariffID")
                REFERENCES "Tariffs" ("TariffID")
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS "Forecast" (
            "ForecastID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "MeterID" INTEGER NOT NULL,
            "Period" TEXT NOT NULL,
            "PredictedValue" REAL NOT NULL,
            "PredictedAmount" REAL NOT NULL,
            "Confidence" REAL,
            "CreatedAT" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY ("MeterID")
                REFERENCES "Meters" ("MeterID")
                ON DELETE CASCADE
        );


        CREATE TABLE IF NOT EXISTS "BankCards" (

        "CardID" INTEGER PRIMARY KEY AUTOINCREMENT,

        "UserID" INTEGER NOT NULL,

        "BankName" TEXT NOT NULL,

        "CardNumber" TEXT NOT NULL,

        "Expiry" TEXT,

        "IsMain" INTEGER DEFAULT 0,

        FOREIGN KEY ("UserID")
            REFERENCES "USER" ("UserID")
            ON DELETE CASCADE
);

        CREATE TABLE IF NOT EXISTS "Benefits" (
            "BenefitID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "PropertyID" INTEGER NOT NULL,
            "UserID" INTEGER NOT NULL,
            "Type" TEXT NOT NULL,
            "Percent" REAL NOT NULL DEFAULT 0
                CHECK ("Percent" BETWEEN 0 AND 100),
            "ValidFrom" TEXT NOT NULL,
            "ValidTo" TEXT,

            FOREIGN KEY ("PropertyID")
                REFERENCES "Properties" ("PropertyID")
                ON DELETE CASCADE,

            FOREIGN KEY ("UserID")
                REFERENCES "USER" ("UserID")
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS "Notifications" (
            "NotificationID"
                INTEGER PRIMARY KEY AUTOINCREMENT,

            "UserID" INTEGER NOT NULL,
            "Type" TEXT NOT NULL,
            "Message" TEXT NOT NULL,
            "ScheduledAT" TEXT,
            "IsSent" INTEGER NOT NULL DEFAULT 0
                CHECK ("IsSent" IN (0, 1)),
            "SentAT" TEXT,

            FOREIGN KEY ("UserID")
                REFERENCES "USER" ("UserID")
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS "AuditLog" (
            "LogID" INTEGER PRIMARY KEY AUTOINCREMENT,
            "UserID" INTEGER,
            "Action" TEXT NOT NULL,
            "EntityType" TEXT NOT NULL,
            "EntityID" INTEGER,
            "Timestamp" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "IpAddress" TEXT,

            FOREIGN KEY ("UserID")
                REFERENCES "USER" ("UserID")
                ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS "idx_meters_property"
            ON "Meters" ("PropertyID");

        CREATE INDEX IF NOT EXISTS "idx_readings_meter_date"
            ON "Readings" (
                "MeterID",
                "ReadingDate"
            );

        CREATE INDEX IF NOT EXISTS "idx_calculations_reading"
            ON "Calculations" ("ReadingID");

        CREATE INDEX IF NOT EXISTS "idx_calculations_tariff"
            ON "Calculations" ("TariffID");

        CREATE INDEX IF NOT EXISTS "idx_forecast_meter"
            ON "Forecast" ("MeterID");

        CREATE INDEX IF NOT EXISTS "idx_notifications_user"
            ON "Notifications" ("UserID");

        CREATE INDEX IF NOT EXISTS "idx_audit_user"
            ON "AuditLog" ("UserID");
        """
    )


def _seed_demo_data(
    connection: sqlite3.Connection,
) -> None:
    """Insert demonstration data into a new database."""
    user = connection.execute(
        """
        SELECT "UserID"
        FROM "USER"
        WHERE "Email" = ?
        """,
        ("demo@example.com",),
    ).fetchone()

    if user is not None:
        return

    user_cursor = connection.execute(
        """
        INSERT INTO "USER" (
            "Email",
            "Password",
            "FullName",
            "Phone",
            "Role"
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "demo@example.com",
            "demo",
            "Вячеслав Карасев",
            "+7 (900) 000-00-00",
            "Владелец",
        ),
    )

    user_id = int(user_cursor.lastrowid)
    connection.execute(
    """
    INSERT INTO "BankCards"
    (
        "UserID",
        "BankName",
        "CardNumber",
        "Expiry",
        "IsMain"
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        user_id,
        "Сбербанк",
        "**** **** **** 1234",
        "12/28",
        1,
    ),
)

    property_cursor = connection.execute(
        """
        INSERT INTO "Properties" (
            "Address",
            "Type",
            "Area",
            "Residents",
            "Region"
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "г. Новосибирск, ул. Ленина, д. 10",
            "Квартира",
            52.4,
            2,
            "Новосибирская область",
        ),
    )

    property_id = int(
        property_cursor.lastrowid
    )

    connection.execute(
        """
        INSERT INTO "UserPropertyRoles" (
            "UserID",
            "PropertyID",
            "Role"
        )
        VALUES (?, ?, ?)
        """,
        (
            user_id,
            property_id,
            "Владелец",
        ),
    )

    tariffs = [
        ("Холодная вода", 130.0),
        ("Горячая вода", 210.0),
        ("Электричество", 10.0),
        ("Газ", 36.0),
    ]

    tariff_ids = {}

    for resource_type, rate in tariffs:
        cursor = connection.execute(
            """
            INSERT INTO "Tariffs" (
                "PropertyID",
                "ResourceType",
                "Rate",
                "ValidFrom",
                "ZoneType"
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                property_id,
                resource_type,
                rate,
                "2026-01-01",
                "Базовый",
            ),
        )

        tariff_ids[resource_type] = int(
            cursor.lastrowid
        )

    meters = [
        (
            "4421580",
            "Холодная вода",
            "2025-01-01",
            "2029-11-15",
        ),
        (
            "4421581",
            "Горячая вода",
            "2025-01-01",
            "2030-04-12",
        ),
        (
            "774512A",
            "Электричество",
            "2025-01-01",
            "2032-10-20",
        ),
    ]

    meter_ids = {}

    for serial_no, meter_type, install_date, verify_date in meters:
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
                serial_no,
                meter_type,
                install_date,
                verify_date,
                "Активен",
                property_id,
            ),
        )

        meter_ids[meter_type] = int(
            cursor.lastrowid
        )

    readings = [
        (
            "Холодная вода",
            342.1,
            "2026-08-01",
        ),
        (
            "Холодная вода",
            349.5,
            "2026-09-01",
        ),
        (
            "Горячая вода",
            208.2,
            "2026-08-01",
        ),
        (
            "Горячая вода",
            214.8,
            "2026-09-01",
        ),
        (
            "Электричество",
            4401.0,
            "2026-08-01",
        ),
        (
            "Электричество",
            4521.0,
            "2026-09-01",
        ),
    ]

    reading_ids = []

    for meter_type, value, reading_date in readings:
        cursor = connection.execute(
            """
            INSERT INTO "Readings" (
                "MeterID",
                "Value",
                "ReadingDate"
            )
            VALUES (?, ?, ?)
            """,
            (
                meter_ids[meter_type],
                value,
                reading_date,
            ),
        )

        reading_ids.append(
            (
                meter_type,
                int(cursor.lastrowid),
            )
        )

    latest_readings = {
        "Холодная вода": (349.5, 342.1),
        "Горячая вода": (214.8, 208.2),
        "Электричество": (4521.0, 4401.0),
    }

    for meter_type, values in latest_readings.items():
        current_value, previous_value = values

        volume = current_value - previous_value

        amount = (
            volume
            * tariffs[
                [item[0] for item in tariffs]
                .index(meter_type)
            ][1]
        )

        latest_reading = connection.execute(
            """
            SELECT "ReadingID"
            FROM "Readings"
            WHERE "MeterID" = ?
            ORDER BY "ReadingDate" DESC,
                     "ReadingID" DESC
            LIMIT 1
            """,
            (meter_ids[meter_type],),
        ).fetchone()

        connection.execute(
            """
            INSERT INTO "Calculations" (
                "ReadingID",
                "TariffID",
                "Volume",
                "Amount",
                "PeriodStart",
                "PeriodEnd",
                "IsPaid"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                latest_reading["ReadingID"],
                tariff_ids[meter_type],
                volume,
                amount,
                "2026-09-01",
                "2026-09-30",
                0,
            ),
        )

        predicted_value = current_value * 1.05
        predicted_amount = amount * 1.05

        connection.execute(
            """
            INSERT INTO "Forecast" (
                "MeterID",
                "Period",
                "PredictedValue",
                "PredictedAmount",
                "Confidence"
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                meter_ids[meter_type],
                "2026-10",
                predicted_value,
                predicted_amount,
                0.82,
            ),
        )

    connection.execute(
        """
        INSERT INTO "Benefits" (
            "PropertyID",
            "UserID",
            "Type",
            "Percent",
            "ValidFrom"
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            property_id,
            user_id,
            "Социальная льгота",
            10.0,
            "2026-01-01",
        ),
    )

    connection.execute(
        """
        INSERT INTO "Notifications" (
            "UserID",
            "Type",
            "Message",
            "ScheduledAT",
            "IsSent"
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            "Показания",
            "Не забудьте передать показания счётчиков.",
            "2026-10-25 09:00:00",
            0,
        ),
    )

    connection.execute(
        """
        INSERT INTO "AuditLog" (
            "UserID",
            "Action",
            "EntityType",
            "EntityID",
            "IpAddress"
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            "CREATE",
            "Property",
            property_id,
            "127.0.0.1",
        ),
    )


def init_database() -> None:
    """Create and initialize the current SQLite database."""

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if DATABASE_PATH.exists():
        with get_connection() as connection:
            if not _schema_is_current(connection):
                raise RuntimeError(
                    "Текущая база housing.db имеет "
                    "несовместимую структуру. "
                    "Удалите только housing.db "
                    "при полностью закрытой программе."
                )

    with get_connection() as connection:
        _create_schema(connection)

        # Создание демо-пользователя,
        # жилья, приборов и банковских карт
        _seed_demo_data(connection)

        connection.execute(
            f"PRAGMA user_version = {SCHEMA_VERSION}"
        )

        connection.commit()

        