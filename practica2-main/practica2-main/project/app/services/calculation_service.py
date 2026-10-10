from app.database.connection import get_connection
from datetime import datetime


def create_calculation(reading_id: int):

    with get_connection() as connection:

        reading = connection.execute(
            """
            SELECT
                r.ReadingID,
                r.MeterID,
                r.Value,
                r.ReadingDate,
                m.Type,
                m.PropertyID
            FROM Readings r
            JOIN Meters m
            ON m.MeterID = r.MeterID
            WHERE r.ReadingID=?
            """,
            (reading_id,)
        ).fetchone()


        if not reading:
            return


        # предыдущее показание

        previous = connection.execute(
            """
            SELECT Value
            FROM Readings
            WHERE MeterID=?
            AND ReadingID<?
            ORDER BY ReadingID DESC
            LIMIT 1
            """,
            (
                reading["MeterID"],
                reading_id,
            )
        ).fetchone()


        if not previous:
            return


        volume = (
            float(reading["Value"])
            -
            float(previous["Value"])
        )


        tariff = connection.execute(
            """
            SELECT
                TariffID,
                Rate
            FROM Tariffs
            WHERE PropertyID=?
            AND ResourceType=?
            """,
            (
                reading["PropertyID"],
                reading["Type"],
            )
        ).fetchone()


        if not tariff:
            return


        amount = volume * float(tariff["Rate"])


        period = reading["ReadingDate"][:7]


        connection.execute(
            """
            INSERT INTO Calculations
            (
                ReadingID,
                TariffID,
                Volume,
                Amount,
                PeriodStart,
                PeriodEnd,
                IsPaid
            )
            VALUES
            (?,?,?,?,?,?,0)
            """,
            (
                reading_id,
                tariff["TariffID"],
                volume,
                amount,
                period+"-01",
                period+"-30",
            )
        )

        connection.commit()