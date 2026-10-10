from app.database.connection import get_connection


def get_cards():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 
            id,
            card_number,
            bank_name,
            expiry_date,
            is_main
        FROM BankCards
        """
    )

    rows = cursor.fetchall()

    connection.close()

    cards = []

    for row in rows:
        cards.append(
            {
                "id": row[0],
                "card_number": row[1],
                "bank_name": row[2],
                "expiry_date": row[3],
                "is_main": row[4],
            }
        )

    return cards



def add_card(
    card_number,
    bank_name,
    expiry_date,
    is_main=False
):

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO BankCards
        (
            card_number,
            bank_name,
            expiry_date,
            is_main
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            card_number,
            bank_name,
            expiry_date,
            is_main,
        )
    )


    connection.commit()
    connection.close()



def delete_card(card_id):

    connection = get_connection()

    connection.execute(
        """
        DELETE FROM BankCards
        WHERE id = ?
        """,
        (
            card_id,
        )
    )

    connection.commit()

    connection.close()