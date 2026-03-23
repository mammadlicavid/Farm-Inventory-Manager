from django.db import connection
cursor = connection.cursor()
cursor.execute('DROP TABLE IF EXISTS suppliers_supplier CASCADE;')
cursor.execute("DELETE FROM django_migrations WHERE app='suppliers';")
print("Reset successful")
