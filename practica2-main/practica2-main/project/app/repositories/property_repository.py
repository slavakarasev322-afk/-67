from app.database.connection import get_connection


def get_properties(user_id=1):
    """
    Получить все объекты пользователя
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            propertyID,
            address,
            type,
            area,
            resident,
            region,
            createdAT
        FROM Properties
        WHERE userID = ?
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    connection.close()


    return [
        {
            "id": row[0],
            "address": row[1],
            "type": row[2],
            "area": row[3],
            "resident": row[4],
            "region": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]



def get_property(property_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            propertyID,
            address,
            type,
            area,
            resident,
            region,
            createdAT
        FROM Properties
        WHERE propertyID = ?
        """,
        (property_id,)
    )

    row = cursor.fetchone()

    connection.close()


    if row is None:
        return None


    return {
        "id": row[0],
        "address": row[1],
        "type": row[2],
        "area": row[3],
        "resident": row[4],
        "region": row[5],
        "created_at": row[6],
    }



def add_property(
        user_id,
        address,
        property_type,
        area,
        resident,
        region
):

    connection = get_connection()


    connection.execute(
        """
        INSERT INTO Properties
        (
            userID,
            address,
            type,
            area,
            resident,
            region,
            createdAT
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            user_id,
            address,
            property_type,
            area,
            resident,
            region
        )
    )


    connection.commit()
    connection.close()



def update_property(
        property_id,
        address,
        area,
        resident,
        region
):

    connection = get_connection()


    connection.execute(
        """
        UPDATE Properties
        SET
            address = ?,
            area = ?,
            resident = ?,
            region = ?

        WHERE propertyID = ?
        """,
        (
            address,
            area,
            resident,
            region,
            property_id
        )
    )


    connection.commit()
    connection.close()



def delete_property(property_id):

    connection = get_connection()


    connection.execute(
        """
        DELETE FROM Properties
        WHERE propertyID = ?
        """,
        (property_id,)
    )


    connection.commit()
    connection.close()