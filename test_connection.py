import pymysql

# Parámetros de conexión
config = {
    "host": "localhost",
    "user": "crm_user",
    "password": "TuPasswordFuerte123!",
    "database": "crm_pyme",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

try:
    print("🔄 Conectando a MySQL...")
    connection = pymysql.connect(**config)
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE() AS db, VERSION() AS version;")
        result = cursor.fetchone()
        print(f"✅ Conectado a la base '{result['db']}' (versión {result['version']})")

except Exception as e:
    print("❌ Error al conectar:", e)

finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("🔚 Conexión cerrada correctamente.")
