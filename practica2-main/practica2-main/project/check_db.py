from app.services.account_service import initialize_auth_schema
from app.database.connection import get_connection

initialize_auth_schema()

with get_connection() as conn:
    columns = conn.execute(
'PRAGMA table_info("AppUsers")'
).fetchall()


print("Столбцы AppUsers после инициализации:")
for column in columns:
    print("-", column["name"])

