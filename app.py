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
# Variable para el panel de "Referencias especiales por ciudad"
referencias_seleccionadas: Dict[str, List[dict]] = {} 

equivalencias = {
    "AK200ZW": 6, "ATUL RIK": 12, "AK250CR4 EFI": 2, "HIMALAYAN 452": 2,
    "HNTR 350": 2, "300AC": 2, "300DS": 2, "300RALLY": 2, "CLASSIC 350": 2,
    "CONTINENTAL GT 650": 2, "GBR 450": 2, "HIMALAYAN": 2, "INTERCEPTOR INT 650": 2,
    "METEOR 350": 2, "METEOR 350 STELLAR": 2, "SCRAM 411": 2, "SCRAM 411 SPIRIT": 2,
    "SHOTGUN 650": 650, "SUPER METEOR 650": 2, "AK110NV EIII": 1, "AK125CR4 EIII": 1,
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
            
    return item_seleccionado[mejor_w], dp[mejor_w][0]

# --- RUTAS FLASK ---
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
    global conteo_ciudades, datos_motos_original, referencias_seleccionadas
    file = request.files.get("file")
    if file:
        df = pd.read_excel(file)
        # Filtro Estado 40
        df = df[df["Estado Satf"] == 40].copy()
        
        # Conversión de fecha
        if 'Reserva' in df.columns:
            df['Reserva'] = pd.to_datetime(df['Reserva'], errors='coerce')
            
        df['peso_espacio'] = df['COD INT'].apply(get_equivalencia)
        datos_motos_original = df
        conteo_ciudades = df["Descr EXXIT"].value_counts().to_dict()

        # *** RECONSTRUCCIÓN DEL REPORTE DE REFERENCIAS ESPECIALES PARA EL DASHBOARD ***
        referencias_seleccionadas = {}
        if "COD INT" in df.columns and "Descr EXXIT" in df.columns:
            reporte = (
                df.groupby([df["Descr EXXIT"].astype(str).str.upper(), "COD INT"])
                .size()
                .reset_index(name="Cantidad")
            )
            for _, row in reporte.iterrows():
                ciudad = row["Descr EXXIT"]
                cod_int = row["COD INT"]
                eq = get_equivalencia(cod_int)
                if eq <= 1: continue # Solo referencias "especiales" (eq > 1)

                cant = int(row["Cantidad"])
                total = cant * eq
                referencias_seleccionadas.setdefault(ciudad, [])
                
                # descripción representativa
                mask = (
                    (df["Descr EXXIT"].astype(str).str.upper() == ciudad)
                    & (df["COD INT"] == cod_int)
                )
                descripcion_ejemplo = (
                    df.loc[mask, "Descripcion"].iloc[0]
                    if "Descripcion" in df.columns and not df.loc[mask].empty
                    else str(cod_int)
                )

                referencias_seleccionadas[ciudad].append(
                    {
                        "cod_int": cod_int,
                        "descripcion": descripcion_ejemplo,
                        "cantidad": cant,
                        "equivalencia": eq,
                        "total": total,
                        "usar": True, # Estado por defecto
                    }
                )
        # *****************************************************************************

    session["mensaje"] = "✅ Archivo cargado correctamente"
    return redirect(url_for("dashboard"))

@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    global referencias_seleccionadas
    for ciudad, refs in referencias_seleccionadas.items():
        for r in refs:
            # Revisa si el checkbox estaba marcado en el formulario POST
            key = f"{ciudad}_{r['cod_int']}"
            r["usar"] = key in request.form 
    session["mensaje"] = "✅ Selección guardada"
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    data = {
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",") if c.strip()],
    }
    vehiculos.append(data)
    session["mensaje"] = "✅ Vehículo registrado"
    return redirect(url_for("dashboard"))


@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    if datos_motos_original.empty or not vehiculos: return "Cargue datos y registre vehículos.", 400
    
    pendientes = datos_motos_original.copy()
    output = io.BytesIO()
    
    # Agrupar vehículos por sus ciudades permitidas (como tupla) para procesar flotas juntas
    vehiculos_por_ciudad = defaultdict(list)
    for v in vehiculos:
        if v["ciudades"]:
            ciudad_clave = tuple(sorted([c.strip().upper() for c in v["ciudades"]]))
            vehiculos_por_ciudad[ciudad_clave].append(v)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        for ciudad_clave, flota_vehiculos in vehiculos_por_ciudad.items():
            
            for v in flota_vehiculos:
                capacidad_camion = v["cantidad_motos"]
                
                mask_vehiculo = pendientes["Descr EXXIT"].str.upper().isin(v["ciudades"])
                posibles = pendientes[mask_vehiculo].copy()
                
                if posibles.empty: continue

                if 'Reserva' in posibles.columns:
                    posibles = posibles.sort_values(by=['Reserva', 'Dirección 1'], ascending=[True, True])
                
                grupos_direccion = posibles.groupby("Dirección 1").agg(
                    peso_espacio=('peso_espacio', 'sum'),
                    indices_originales=('peso_espacio', lambda x: list(x.index))
                ).reset_index()
                
                items_para_mochila = [{"id": i, "peso": row["peso_espacio"]} for i, row in grupos_direccion.iterrows()]
                
                indices_grupo_elegidos, peso_logrado = _knapsack_max_peso_min_items(items_para_mochila, capacidad_camion)
                
                min_peso_requerido = capacidad_camion * 0.95
                
                if peso_logrado >= min_peso_requerido:
                    indices_finales_df = []
                    for idx_grupo in indices_grupo_elegidos:
                        indices_finales_df.extend(grupos_direccion.iloc[idx_grupo]["indices_originales"])
                    
                    asignacion_df = pendientes.loc[indices_finales_df].copy()
                    
                    if not asignacion_df.empty:
                        nombre_hoja = _excel_safe_sheet_name(v["placa"])
                        asignacion_df = asignacion_df.sort_values(by=['Reserva', 'Dirección 1'], ascending=[True, True])
                        asignacion_df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                        
                        pendientes = pendientes.drop(asignacion_df.index)

        if not pendientes.empty:
            if 'Reserva' in pendientes.columns:
                 pendientes = pendientes.sort_values(by=['Reserva', 'Dirección 1'], ascending=[True, True])
            pendientes.to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(
        output, 
        as_attachment=True, 
        download_name="Planeador_Despacho_Final.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
