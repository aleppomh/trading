"""
Script para migrar la tabla OTCPair y añadir las nuevas columnas
"""
import logging
from app import app, db

# Configuración del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def modify_table_schema():
    """Modificar el esquema de la tabla usando SQL directo"""
    try:
        # Conectar a la base de datos directamente sin usar SQLAlchemy
        from flask import current_app
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Obtener la URL de la DB
        db_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        
        # Conectar a PostgreSQL
        connection = psycopg2.connect(db_url)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Crear un cursor
        cursor = connection.cursor()
        
        # 1. Verificar si la columna display_name existe
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='otc_pairs' AND column_name='display_name'")
        if cursor.fetchone() is None:
            logger.info("Agregando columna display_name...")
            cursor.execute("ALTER TABLE otc_pairs ADD COLUMN display_name VARCHAR(20)")
            cursor.execute("UPDATE otc_pairs SET display_name = REPLACE(symbol, '-OTC', '')")
        
        # 2. Verificar si la columna base_price existe
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='otc_pairs' AND column_name='base_price'")
        if cursor.fetchone() is None:
            logger.info("Agregando columna base_price...")
            cursor.execute("ALTER TABLE otc_pairs ADD COLUMN base_price FLOAT DEFAULT 1.0")
        
        # 3. Verificar si la columna volatility existe
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='otc_pairs' AND column_name='volatility'")
        if cursor.fetchone() is None:
            logger.info("Agregando columna volatility...")
            cursor.execute("ALTER TABLE otc_pairs ADD COLUMN volatility FLOAT DEFAULT 0.5")
        
        # 4. Verificar si la columna payout_rate existe
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='otc_pairs' AND column_name='payout_rate'")
        if cursor.fetchone() is None:
            logger.info("Agregando columna payout_rate...")
            cursor.execute("ALTER TABLE otc_pairs ADD COLUMN payout_rate INTEGER DEFAULT 80")
        
        # Cerrar cursor y conexión
        cursor.close()
        connection.close()
        
        logger.info("Migración completada correctamente")
        return True
    
    except Exception as e:
        logger.error(f"Error durante la migración: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        modify_table_schema()