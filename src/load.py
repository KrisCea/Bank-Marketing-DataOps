# src/load.py
# Objetivo: Cargar los datos validados a una base de datos SQLite.
# Se crea tabla con estructura dinamica y se insertan los datos.

import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime

# Crear carpeta logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename='logs/load.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_to_database(csv_path, db_path, table_name):
    """
    Carga los datos validados a una base de datos SQLite.
    
    Operaciones:
    1. Carga el dataset desde CSV
    2. Conecta a la base de datos SQLite
    3. Crea la tabla si no existe
    4. Inserta los datos fila por fila con manejo de errores
    5. Genera un reporte de la carga
    
    Parametros:
    csv_path (str): Ruta del archivo CSV a cargar
    db_path (str): Ruta del archivo de base de datos SQLite
    table_name (str): Nombre de la tabla donde se insertaran los datos
    
    Retorna:
    tuple: (registros_exitosos, registros_fallidos)
    """
    conn = None
    try:
        # 1. Cargar datos validados
        df = pd.read_csv(csv_path)
        print(f"[INFO] Cargando {len(df)} registros desde {csv_path}")
        logging.info(f"Iniciando carga de {len(df)} registros")
        
        # 2. Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 3. Crear tabla si no existe
        #    Inferir tipo SQL basado en el tipo de dato de pandas
        columnas = []
        for col in df.columns:
            if df[col].dtype in ['int64', 'int32']:
                sql_type = 'INTEGER'
            elif df[col].dtype in ['float64', 'float32']:
                sql_type = 'REAL'
            else:
                sql_type = 'TEXT'
            columnas.append(f'"{col}" {sql_type}')
        
        # Agregar columna id como clave primaria autoincrementable
        create_table_sql = f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join(columnas)}
        )
        '''
        cursor.execute(create_table_sql)
        logging.info(f"Tabla '{table_name}' creada o verificada")
        
        # 4. Insertar datos con manejo de errores por fila
        registros_exitosos = 0
        registros_fallidos = 0
        
        for idx, row in df.iterrows():
            try:
                # Convertir fila a valores
                valores = list(row.to_dict().values())
                columnas_lista = list(row.index)
                
                # Construir consulta INSERT
                placeholders = ','.join(['?'] * len(columnas_lista))
                columnas_str = ','.join([f'"{col}"' for col in columnas_lista])
                insert_sql = f'INSERT INTO {table_name} ({columnas_str}) VALUES ({placeholders})'
                
                cursor.execute(insert_sql, valores)
                registros_exitosos += 1
                
            except Exception as error_fila:
                registros_fallidos += 1
                logging.warning(f"Error insertando fila {idx}: {str(error_fila)}")
        
        # 5. Confirmar transaccion
        conn.commit()
        
        # 6. Generar reporte de carga
        reporte = {
            'fecha_carga': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'archivo_origen': csv_path,
            'tabla_destino': f'{db_path} -> {table_name}',
            'registros_totales': len(df),
            'registros_exitosos': registros_exitosos,
            'registros_fallidos': registros_fallidos,
            'carga_exitosa': registros_fallidos == 0
        }
        
        # Guardar reporte
        reporte_path = "data/reports/load_report.csv"
        os.makedirs(os.path.dirname(reporte_path), exist_ok=True)
        reporte_df = pd.DataFrame([reporte])
        reporte_df.to_csv(reporte_path, index=False)
        
        # Mostrar resultados en consola
        print("\n" + "=" * 50)
        print("RESULTADO DE CARGA A BASE DE DATOS")
        print("=" * 50)
        print(f"Registros insertados: {registros_exitosos}")
        print(f"Registros con error: {registros_fallidos}")
        print(f"Base de datos: {db_path}")
        print(f"Tabla: {table_name}")
        print(f"Reporte: {reporte_path}")
        
        if registros_fallidos == 0:
            print("\nCARGA EXITOSA: Todos los registros fueron insertados")
            logging.info(f"Carga completada: {registros_exitosos} registros")
        else:
            print(f"\nALERTA: {registros_fallidos} registros no se insertaron")
            logging.warning(f"Carga parcial: {registros_fallidos} fallidos")
        
        return registros_exitosos, registros_fallidos
        
    except Exception as e:
        logging.error(f"Error critico: {str(e)}")
        print(f"[ERROR] {str(e)}")
        if conn:
            conn.rollback()
        return 0, 0
        
    finally:
        if conn:
            conn.close()
            logging.info("Conexion a base de datos cerrada")

if __name__ == "__main__":
    # Determinar que archivo cargar
    archivo_csv = "data/processed/02_bank_clean.csv"
    if not os.path.exists(archivo_csv):
        print("[INFO] No se encuentra archivo limpio. Usando archivo ingerido.")
        archivo_csv = "data/processed/02_bank_ingested.csv"
    
    archivo_db = "data/bank_marketing.db"
    nombre_tabla = "clientes"
    
    load_to_database(archivo_csv, archivo_db, nombre_tabla)