from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter, defaultdict
import os
import io
from typing import Dict, List, Optional, Set, Tuple
import datetime
import itertools

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- VARIABLES GLOBALES ---
vehiculos: List[dict] = []
conteo_ciudades: Dict[str, int] = {}
datos_motos_original = pd.DataFrame()
referencias_seleccionadas: Dict[str, List[dict]] = {}
equivalencias = {
    "AK200ZW": 6, "ATUL RIK": 12, "AK250CR4 EFI": 2, "HIMALAYAN 452": 2,
    "HNTR 350": 2, "300AC": 2, "300DS": 2, "300RALLY": 2, "CLASSIC 350": 2,
    "CONTINENTAL GT 650": 2, "GBR 450": 2, "HIMALAYAN": 2, "INTERCEPTOR INT 650": 2,
    "METEOR 350": 2, "METEOR 350 STELLAR": 2, "SCRAM 411": 2, "SCRAM 411 SPIRIT": 2,
    "SHOTGUN 650": 2, "SUPER METEOR 650": 2, "AK110NV EIII": 1, "AK125CR4 EIII": 1,
    "AK125DYN PRO+": 1, "AK125FLEX EIII": 1, "AK125NKD EIII": 1, "AK125T-4": 1,
    "AK125TTR EIII": 1, "AK150CR4": 1, "AK200DS+": 1, "AK200TTR EIII": 1, "DYNAMIC RX": 1,
}

# --- FUNCIONES DE APOYO ---

def get_equivalencia(cod_int: str) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "": return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def _excel_safe_sheet_name(name: str) -> str:
    safe = (str(name) if name else "CAMION").strip()
    for ch in ['/', '\\', ':', '*', '?', '[', ']']: safe = safe.replace(ch, "-")
    return safe[:31]

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int) -> Tuple[List[int], int]:
    """
    Maximiza peso (espacios) y desempata con menos items (direcciones).
    Retorna (indices_seleccionados, peso_total_logrado)
    """
    n = len(items)
    dp = [(0, 0)] * (capacidad + 1)
    item_seleccionado = [[] for _ in range(capacidad + 1)]

    for i, item in enumerate(items):
        w_i = item['peso']
        for w in range(capacidad, w_i - 1, -1):
            # Tupla (peso total, -num items)
            cand_val = (dp[w - w_i][0] + w_i, dp[w - w_i][1] - 1) 
            if cand_val > dp[w]:
                dp[w] = cand_val
                item_seleccionado[w] = item_seleccionado[w - w_i] + [item['id']]

    mejor_w = 0
    mejor_val = (-1, -1)
    for w in range(capacidad + 1):
        if dp[w] > mejor_val:
            mejor_val = dp[w]
            mejor_w = w
            
    return item_seleccionado[mejor_w], dp[mejor_w][0] # Retorna indices y peso total logrado

# --- RUTAS FLASK (login, dashboard, upload, registrar_vehiculo - sin cambios) ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["contrasena"] == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html", ciudades=conteo_ciudades, referencias=referencias_seleccionadas, vehiculos=vehiculos)

@app.route("/upload", methods=["POST"])
def upload():
    global conteo_ciudades, datos_motos_original
    file = request.files.get("file")
    if file:
        df = pd.read_excel(file)
        df = df[df["Estado Satf"] == 40].copy()
        if 'Reserva' in df.columns:
            df['Reserva'] = pd.to_datetime(df['Reserva'], errors='coerce')
        df['peso_espacio'] = df['COD INT'].apply(get_equivalencia)
        datos_motos_original = df
        conteo_ciudades = df["Descr EXXIT"].value_counts().to_dict()
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    vehiculos.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",") if c.strip()]
    })
    return redirect(url_for("dashboard"))


@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    if datos_motos_original.empty or not vehiculos: return "Cargue datos y registre vehículos.", 400
    
    pendientes = datos_motos_original.copy()
    output = io.BytesIO()
    
    # Agrupar vehículos por ciudad principal única para procesar flotas juntas
    vehiculos_por_ciudad = defaultdict(list)
    for v in vehiculos:
        if v["ciudades"]:
            # Usamos una tupla de ciudades como clave para manejar multi-ciudad como un grupo único
            ciudad_clave = tuple(sorted([c.strip().upper() for c in v["ciudades"]]))
            vehiculos_por_ciudad[ciudad_clave].append(v)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        for ciudad_clave, flota_vehiculos in vehiculos_por_ciudad.items():
            
            # Procesamos CADA vehículo de la flota SECUENCIALMENTE para aplicar la regla del 95%
            for v in flota_vehiculos:
                capacidad_camion = v["cantidad_motos"]
                
                # Filtrar inventario que puede ser llevado por ESTE vehículo
                mask_vehiculo = pendientes["Descr EXXIT"].str.upper().isin(v["ciudades"])
                posibles = pendientes[mask_vehiculo].copy()
                
                if posibles.empty: continue

                # Ordenar por fecha de reserva (ascendente/más antigua primero)
                if 'Reserva' in posibles.columns:
                    posibles = posibles.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
                
                # Agrupar por Direccion 1 para mantener indivisibilidad
                # Usamos el índice de 'posibles' como ID para rastrear las filas originales
                grupos_direccion = posibles.groupby("Direccion 1").agg(
                    peso_espacio=('peso_espacio', 'sum'),
                    indices_originales=('peso_espacio', lambda x: list(x.index)) # Guardamos los índices originales
                ).reset_index()
                
                items_para_mochila = [{"id": i, "peso": row["peso_espacio"]} for i, row in grupos_direccion.iterrows()]
                
                # Resolver Mochila (obtenemos índices del grupo y peso total logrado)
                indices_grupo_elegidos, peso_logrado = _knapsack_max_peso_min_items(items_para_mochila, capacidad_camion)
                
                # *** APLICAR REGLA DEL 95% ***
                min_peso_requerido = capacidad_camion * 0.95
                
                if peso_logrado >= min_peso_requerido:
                    # Si cumple el 95%, asignamos
                    indices_finales_df = []
                    for idx_grupo in indices_grupo_elegidos:
                        # Recuperamos los índices originales del DF 'posibles' que componen este grupo/dirección
                        indices_finales_df.extend(grupos_direccion.iloc[idx_grupo]["indices_originales"])
                    
                    # Extraer las filas correspondientes de 'pendientes' usando los índices originales
                    asignacion_df = pendientes.loc[indices_finales_df].copy()
                    
                    if not asignacion_df.empty:
                        nombre_hoja = _excel_safe_sheet_name(v["placa"])
                        # Asegura que la hoja de Excel muestre el orden correcto por fecha/dirección
                        asignacion_df = asignacion_df.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
                        asignacion_df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                        
                        # ELIMINAR del inventario pendiente global
                        pendientes = pendientes.drop(asignacion_df.index)
                
                # Si no cumple el 95%, este camión se salta y sus posibles motos quedan en 'pendientes' para la hoja final.

        # Hoja final con lo que NO cupo en NINGÚN camión o no cumplió el 95%
        if not pendientes.empty:
            if 'Reserva' in pendientes.columns:
                 pendientes = pendientes.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
            pendientes.to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(
        output, 
        as_attachment=True, 
        download_name="Planeador_Despacho_95pct_Minimo.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
