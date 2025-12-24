from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
import io
from typing import Dict, List, Optional, Set, Tuple
import datetime # Importamos datetime para el manejo de fechas

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

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int) -> List[int]:
    """
    Maximiza peso (espacios) y desempata con menos items (direcciones).
    items: lista de {'id': indice_grupo, 'peso': total_espacios_direccion}
    """
    # ... (el algoritmo knapsack es el mismo que antes, es un algoritmo matemático) ...
    n = len(items)
    dp = [(0, 0)] * (capacidad + 1)
    item_seleccionado = [[] for _ in range(capacidad + 1)]

    for i, item in enumerate(items):
        w_i = item['peso']
        for w in range(capacidad, w_i - 1, -1):
            nuevo_peso = dp[w - w_i] + w_i
            nuevos_items = dp[w - w_i] - 1
            
            if nuevo_peso > dp[w] or (nuevo_peso == dp[w] and nuevos_items > dp[w]):
                dp[w] = (nuevo_peso, nuevos_items)
                item_seleccionado[w] = item_seleccionado[w - w_i] + [item['id']]

    mejor_w = 0
    mejor_val = (-1, -1)
    for w in range(capacidad + 1):
        if dp[w] > mejor_val or (dp[w] == mejor_val and dp[w] > mejor_val):
            mejor_val = dp[w]
            mejor_w = w
            
    return item_seleccionado[mejor_w]

# --- RUTAS FLASK ---

@app.route("/upload", methods=["POST"])
def upload():
    global conteo_ciudades, datos_motos_original
    file = request.files.get("file")
    if file:
        df = pd.read_excel(file)
        df = df[df["Estado Satf"] == 40].copy()
        
        # *** NUEVO: Convertir la columna 'Reserva' a formato de fecha y hora ***
        if 'Reserva' in df.columns:
            # Forzamos conversión, los errores se convierten a NaT (Not a Time)
            df['Reserva'] = pd.to_datetime(df['Reserva'], errors='coerce')
            # Rellenamos NaT con una fecha muy lejana si es necesario, 
            # pero sort_values maneja NaT bien poniéndolos al final por defecto.

        df['peso_espacio'] = df['COD INT'].apply(get_equivalencia)
        datos_motos_original = df
        conteo_ciudades = df["Descr EXXIT"].value_counts().to_dict()
    return redirect(url_for("dashboard"))

# ... (login, dashboard, registrar_vehiculo rutas son las mismas) ...
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
    return render_template("dashboard.html", ciudades=conteo_ciudades, 
                           referencias=referencias_seleccionadas, vehiculos=vehiculos)

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
    if datos_motos_original.empty: return "Cargue un archivo primero", 400
    
    pendientes = datos_motos_original.copy()
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for v in vehiculos:
            # 1. Filtrar pendientes por las ciudades del camión
            mask_ciudades = pendientes["Descr EXXIT"].str.upper().isin(v["ciudades"])
            posibles = pendientes[mask_ciudades].copy()
            
            if posibles.empty: continue
            
            # *** NUEVO: Ordenar por fecha de reserva (ascendente/más antigua primero) ***
            if 'Reserva' in posibles.columns:
                # Ordena primero por fecha de reserva ascendente, luego por dirección
                posibles = posibles.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
            
            # 2. Agrupar por Direccion 1 (para no dividir pedidos)
            grupos = posibles.groupby("Direccion 1").agg({
                "peso_espacio": "sum"
            }).reset_index()
            
            # 3. Resolver Mochila
            items_para_mochila = [{"id": i, "peso": row["peso_espacio"]} for i, row in grupos.iterrows()]
            indices_elegidos = _knapsack_max_peso_min_items(items_para_mochila, v["cantidad_motos"])
            
            direcciones_a_cargar = grupos.iloc[indices_elegidos]["Direccion 1"].tolist()
            
            # 4. Extraer las filas correspondientes
            # Usamos merge para mantener el orden de 'posibles' que ya está ordenado por fecha
            asignacion = pd.merge(posibles, pd.DataFrame({"Direccion 1": direcciones_a_cargar}), on="Direccion 1", how="inner")
            
            if not asignacion.empty:
                nombre_hoja = _excel_safe_sheet_name(v["placa"])
                # Asegura que la hoja de Excel muestre el orden correcto
                asignacion.to_excel(writer, sheet_name=nombre_hoja, index=False)
                
                # 5. ELIMINAR del inventario pendiente para que no se repitan
                # Usamos isin invertido (~) para seleccionar las filas que NO están en la asignacion
                pendientes = pendientes[~pendientes.index.isin(asignacion.index)]

        # Hoja final con lo que NO cupo
        if not pendientes.empty:
            pendientes = pendientes.sort_values(by=['Reserva', 'Direccion 1'], ascending=[True, True])
            pendientes.to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(
        output, 
        as_attachment=True, 
        download_name="Planeador_Despacho_2025.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
