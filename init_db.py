from sqlalchemy import create_engine
from models import Base

# URL de conexión a MySQL
DB_URL = "mysql+pymysql://crm_user:TuPasswordFuerte123!@localhost:3306/crm_pyme?charset=utf8mb4"

engine = create_engine(DB_URL, echo=True)

print("🔄 Creando tablas en MySQL...")
Base.metadata.create_all(engine)
print("✅ Tablas creadas correctamente en la base crm_pyme.")
