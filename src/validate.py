# src/validate.py
# Objetivo: Validar los datos antes de cargarlos a la base de datos.
# Validaciones: nulos, tipos de datos, rangos de valores.

import pandas as pd
import os
import logging
from datetime import datetime

# Crear carpeta logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename='logs/validate.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def validate_data(input_path, report_path):
    """
    Valida estructural y semanticamente el dataset Bank Marketing.
    
    Validaciones estructurales:
    - Verifica que no haya valores nulos en columnas criticas
    - Comprueba tipos de datos correctos
    
    Validaciones semanticas:
    - Verifica rangos de valores (edad: 0-120, pdays >= -1, campaign >= 1)
    - Comprueba que la variable objetivo solo tenga 0 o 1
    
    Parametros:
    input_path (str): Ruta del archivo a validar
    report_path (str): Ruta donde se guardara el reporte
    
    Retorna:
    bool: True si la validacion es exitosa (sin errores criticos)
    """
    try:
        # Cargar datos
        df = pd.read_csv(input_path)
        errores = []
        advertencias = []
        
        logging.info(f"Iniciando validacion de {input_path}")
        print(f"[INFO] Validando {input_path}...")
        
        # ========== VALIDACIONES ESTRUCTURALES ==========
        
        # 1. Verificar valores nulos en columnas criticas
        #    Estas columnas son esenciales para el modelo
        columnas_criticas = ['age', 'balance', 'duration', 'deposit']
        for col in columnas_criticas:
            if col in df.columns:
                nulos = df[col].isnull().sum()
                if nulos > 0:
                    errores.append(f"Columna {col} tiene {nulos} valores nulos")
                    logging.error(f"Validacion estructural fallida: {col} tiene nulos")
        
        # 2. Verificar tipos de datos esperados
        tipos_esperados = {
            'age': 'int64',
            'deposit': 'int64'
        }
        for col, tipo_esperado in tipos_esperados.items():
            if col in df.columns:
                if str(df[col].dtype) != tipo_esperado:
                    advertencias.append(
                        f"Columna {col} es {df[col].dtype}, se esperaba {tipo_esperado}"
                    )
        
        # ========== VALIDACIONES SEMANTICAS ==========
        
        # 3. Verificar rango de edad (0-120 años)
        if 'age' in df.columns:
            if (df['age'] < 0).any() or (df['age'] > 120).any():
                errores.append("Existen edades fuera del rango valido (0-120 anos)")
        
        # 4. Verificar variable objetivo deposit (solo 0 o 1)
        if 'deposit' in df.columns:
            valores_unicos = df['deposit'].unique()
            if not all(v in [0, 1] for v in valores_unicos):
                errores.append(f"Variable 'deposit' tiene valores invalidos: {valores_unicos}")
        
        # 5. Verificar pdays (dias desde ultimo contacto)
        #    -1 significa sin contacto previo, es valido
        if 'pdays' in df.columns:
            if (df['pdays'] < -1).any():
                errores.append("Variable 'pdays' tiene valores menores a -1 (invalido)")
        
        # 6. Verificar campaign (numero de contactos en esta campaña)
        #    Debe ser al menos 1
        if 'campaign' in df.columns:
            if (df['campaign'] < 1).any():
                advertencias.append("Existen registros con 'campaign' menor a 1")
        
        # 7. Verificar balance (puede ser negativo, pero no extremo)
        if 'balance' in df.columns:
            if (df['balance'] < -10000).any() or (df['balance'] > 100000).any():
                advertencias.append("Existen valores de balance extremos (>100k o <-10k)")
        
        # ========== GENERAR REPORTE ==========
        
        # Crear diccionario con el reporte
        reporte = {
            'fecha_validacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'archivo_validado': input_path,
            'total_registros': len(df),
            'errores_encontrados': len(errores),
            'advertencias_encontradas': len(advertencias),
            'detalle_errores': str(errores),
            'detalle_advertencias': str(advertencias),
            'validacion_exitosa': len(errores) == 0
        }
        
        # Guardar reporte como CSV
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        reporte_df = pd.DataFrame([reporte])
        reporte_df.to_csv(report_path, index=False)
        
        # Guardar reporte como archivo de texto legible
        reporte_txt = report_path.replace('.csv', '.txt')
        with open(reporte_txt, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("REPORTE DE VALIDACION - BANK MARKETING\n")
            f.write("=" * 50 + "\n")
            f.write(f"Fecha: {reporte['fecha_validacion']}\n")
            f.write(f"Archivo: {reporte['archivo_validado']}\n")
            f.write(f"Registros: {reporte['total_registros']}\n")
            f.write(f"Errores criticos: {reporte['errores_encontrados']}\n")
            f.write(f"Advertencias: {reporte['advertencias_encontradas']}\n\n")
            
            if errores:
                f.write("ERRORES:\n")
                for e in errores:
                    f.write(f"  - {e}\n")
            if advertencias:
                f.write("\nADVERTENCIAS:\n")
                for w in advertencias:
                    f.write(f"  - {w}\n")
        
        # Mostrar resultado en consola
        if len(errores) == 0:
            print(f"[OK] VALIDACION EXITOSA: No se encontraron errores criticos")
        else:
            print(f"[ERROR] VALIDACION FALLIDA: Se encontraron {len(errores)} errores")
            for e in errores:
                print(f"   - {e}")
        
        print(f"[INFO] Reporte guardado en: {report_path}")
        logging.info(f"Validacion completada. Errores: {len(errores)}")
        
        return len(errores) == 0
        
    except Exception as e:
        logging.error(f"Error durante validacion: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    # Validar el archivo LIMPIO (despues de clean_transform.py)
    archivo_entrada = "data/processed/02_bank_clean.csv"
    archivo_reporte = "data/reports/validation_report.csv"
    
    # Si el archivo limpio no existe, intentar con el ingerido
    if not os.path.exists(archivo_entrada):
        print("[INFO] No se encuentra archivo limpio. Usando archivo ingerido.")
        archivo_entrada = "data/processed/02_bank_ingested.csv"
    
    validate_data(archivo_entrada, archivo_reporte)