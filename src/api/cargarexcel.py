import sys
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

DB_URL = "sqlite:///database.db"  # Para MySQL o PostgreSQL, cambia la URL
engine = create_engine(DB_URL)
metadata = MetaData()

def create_dynamic_table(table_name, df):
    metadata.reflect(bind=engine)  # Refresca la información de las tablas existentes

    if table_name in metadata.tables:
        print(f"La tabla '{table_name}' ya existe. Insertando datos...")
    else:
        print(f"Creando tabla '{table_name}'...")
        columns = [Column("id", Integer, primary_key=True, autoincrement=True)]
        for column_name in df.columns:
            columns.append(Column(column_name, String(255)))  # Se usa String, pero puede cambiarse

        table = Table(table_name, metadata, *columns)
        metadata.create_all(engine)
    
    return metadata.tables[table_name]

def process_excel(file_path):
    df = pd.read_excel(file_path)
    
    # Reemplazar espacios en nombres de columnas para evitar problemas en SQL
    df.columns = [col.replace(" ", "_") for col in df.columns]

    table_name = "datos_excel"
    data_table = create_dynamic_table(table_name, df)

    # Insertar datos en la tabla
    with engine.connect() as conn:
        df.to_sql(table_name, con=conn, if_exists="append", index=False)
    
    print("Datos insertados correctamente.")

if __name__ == "__main__":
    file_path = sys.argv[1]
    process_excel(file_path)
