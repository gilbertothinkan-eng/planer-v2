from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter, defaultdict # Importamos defaultdict
import os
import io
from typing import Dict, List, Optional, Set, Tuple
import datetime
import itertools # Importamos itertools para combinaciones

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- VARIABLES GLOBALES (Mismas que antes) ---
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

# --- FUNCIONES DE APOYO (Mismas que antes) ---
def get_equivalencia(cod_int: str) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "": return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def _excel_safe_sheet_name(name: str) -> str:
    safe = (str(name) if name else "CAMION").strip()
    for ch in ['/', '\\', ':', '*', '?', '[', ']']: safe = safe.replace(ch, "-")
    return safe[:31]

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int) -> List[int]:
    # Función Knapsack sin cambios
    n = len(items)
    dp = [(0, 0)] * (capacidad + 1)
    item_seleccionado = [[] for _ in range(capacidad + 1)]
    for i, item in enumerate(items):
        w_i = item['peso']
        for w in range(capacidad, w_i - 1, -1):
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
    return item_seleccionado[mejor_w]

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
    
    # Agrupar vehículos por ciudad principal única para balanceo de carga
    # Usamos la primera ciudad del listado como 'ciudad de referencia' para el grupo
    vehiculos_por_ciudad = defaultdict(list)
    for v in vehiculos:
        if v["ciudades"]:
            ciudad_clave = v["ciudades"][0] # Usamos la primera ciudad como clave de grupo
            vehiculos_por_ciudad[ciudad_clave].append(v)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        for ciudad_clave, flota_vehiculos in vehiculos_por_ciudad.items():
            
            # Identificar todas las ciudades que maneja esta flota combinada
            ciudades_flota_combinada = set(itertools.chain.from_iterable([v['ciudades'] for v in flota_vehiculos]))
            
            # Filtrar inventario que puede ser llevado por ESTA FLOTA
            mask_flota = pendientes["Descr EXXIT"].str.upper().isin(ciudades_flota_combinada)
            inventario_flota = pendientes[mask_flota].copy()
            
            if inventario_flota.empty: continue

            # Ordenar por fecha de reserva (ascendente/más antigua primero)
            if 'Reserva' in inventario_flota.columns:
                inventario_flota = inventario_flota.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
            
            # Agrupar por Direccion 1 para mantener indivisibilidad
            grupos_direccion = inventario_flota.groupby("Direccion 1").agg({"peso_espacio": "sum"}).reset_index()
            
            items_para_distribuir = [{"id": i, "peso": row["peso_espacio"]} for i, row in grupos_direccion.iterrows()]
            
            # Ejecutar lógica de balanceo (Bin Packing Heuristico: First Fit Decreasing)
            # Simplificado: Asignamos secuencialmente a los camiones con más espacio restante
            
            # Inicializar asignaciones
            flota_status = [{"vehiculo": v, "espacio_restante": v["cantidad_motos"], "direcciones_asignadas": []} for v in flota_vehiculos]
            
            # Ordenar items por peso descendente para un mejor ajuste (FFD)
            items_para_distribuir.sort(key=lambda x: x['peso'], reverse=True)
            
            for item in items_para_distribuir:
                item_peso = item['peso']
                item_idx = item['id']
                
                # Encontrar el primer camión con suficiente espacio (First Fit)
                # O mejor, encontrar el camión con *más* espacio para balancear mejor
                best_fit_camion = None
                max_espacio_restante = -1

                for fs in flota_status:
                    if fs["espacio_restante"] >= item_peso and fs["espacio_restante"] > max_espacio_restante:
                        max_espacio_restante = fs["espacio_restante"]
                        best_fit_camion = fs
                
                if best_fit_camion:
                    best_fit_camion["espacio_restante"] -= item_peso
                    best_fit_camion["direcciones_asignadas"].append(grupos_direccion.iloc[item_idx]["Direccion 1"])
                # Si no cabe en ninguno, se queda fuera y va a "NO_ASIGNADAS"
            
            # Escribir los resultados de la flota al Excel
            for fs in flota_status:
                if fs["direcciones_asignadas"]:
                    # Extraer las filas del dataframe original que corresponden a estas direcciones
                    asignacion_df = inventario_flota[inventario_flota["Direccion 1"].isin(fs["direcciones_asignadas"])]
                    
                    if not asignacion_df.empty:
                        nombre_hoja = _excel_safe_sheet_name(fs["vehiculo"]["placa"])
                        asignacion_df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                        
                        # ELIMINAR del inventario pendiente global
                        pendientes = pendientes.drop(asignacion_df.index)

        # Hoja final con lo que NO cupo en NINGUNA flota
        if not pendientes.empty:
            if 'Reserva' in pendientes.columns:
                 pendientes = pendientes.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
            pendientes.to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(
        output, 
        as_attachment=True, 
        download_name="Planeador_Despacho_Optimizado.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
