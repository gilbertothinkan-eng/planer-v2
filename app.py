from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
import io
from typing import Dict, List

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# VARIABLES GLOBALES
# -----------------------------
vehiculos: List[dict] = []
conteo_ciudades: Dict[str, int] = {}
datos_motos_original = pd.DataFrame()

# Tu HTML (dashboard.html) espera estas variables (aunque no uses selección ahora)
referencias_seleccionadas: Dict[str, List[dict]] = {}

# Equivalencias
equivalencias = {
    "AK200ZW": 6, "ATUL RIK": 12, "AK250CR4 EFI": 2, "HIMALAYAN 452": 2,
    "HNTR 350": 2, "300AC": 2, "300DS": 2, "300RALLY": 2, "CLASSIC 350": 2,
    "CONTINENTAL GT 650": 2, "GBR 450": 2, "HIMALAYAN": 2,
    "INTERCEPTOR INT 650": 2, "METEOR 350": 2, "METEOR 350 STELLAR": 2,
    "SCRAM 411": 2, "SCRAM 411 SPIRIT": 2, "SHOTGUN 650": 2,
    "SUPER METEOR 650": 2, "AK110NV EIII": 1, "AK125CR4 EIII": 1,
    "AK125DYN PRO+": 1, "AK125FLEX EIII": 1, "AK125NKD EIII": 1,
    "AK125T-4": 1, "AK125TTR EIII": 1, "AK150CR4": 1,
    "AK200DS+": 1, "AK200TTR EIII": 1, "DYNAMIC RX": 1,
}

# Columnas EXACTAS del detalle (tu formato definido)
COLUMNAS_DETALLE = [
    "Nom PV",
    "No Ped",
    "Descr",
    "Descr EXXIT",
    "Dirección 1",
    "Clnt Envío",
    "ID Prod",
    "Descripcion",
    "ID Serie",
    "Estado Satf",
    "COD INT",
]

# -----------------------------
# FUNCIONES DE APOYO
# -----------------------------
def get_equivalencia(cod_int) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "":
        return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def _excel_safe_sheet_name(name: str) -> str:
    safe = (str(name) if name else "CAMION").strip()
    for ch in ['/', '\\', ':', '*', '?', '[', ']']:
        safe = safe.replace(ch, "-")
    return safe[:31]

def _normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    NO cambia tu lógica.
    Solo asegura que existan nombres esperados para evitar KeyError:
    - Direccion 1 -> Dirección 1 (si viene sin tilde)
    """
    cols = list(df.columns)

    # Dirección 1: acepta con/sin tilde
    if "Dirección 1" not in cols and "Direccion 1" in cols:
        df = df.rename(columns={"Direccion 1": "Dirección 1"})

    return df

def _asegurar_columnas_detalle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para que el Excel SIEMPRE salga con tu estructura fija,
    si falta alguna columna en el DF, la crea vacía.
    """
    for c in COLUMNAS_DETALLE:
        if c not in df.columns:
            df[c] = ""
    return df

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int):
    """
    MISMA lógica: maximiza peso <= capacidad y desempata con menos items (direcciones)
    Retorna (indices_seleccionados, peso_total_logrado)
    """
    dp = [(0, 0)] * (capacidad + 1)  # (peso_total, -num_items)
    elegido = [[] for _ in range(capacidad + 1)]

    for item in items:
        w_i = int(item["peso"])
        if w_i <= 0:
            continue
        for w in range(capacidad, w_i - 1, -1):
            cand = (dp[w - w_i][0] + w_i, dp[w - w_i][1] - 1)
            if cand > dp[w]:
                dp[w] = cand
                elegido[w] = elegido[w - w_i] + [item["id"]]

    mejor_w = 0
    mejor_val = (-1, -1)
    for w in range(capacidad + 1):
        if dp[w] > mejor_val:
            mejor_val = dp[w]
            mejor_w = w

    return elegido[mejor_w], dp[mejor_w][0]

# -----------------------------
# RUTAS FLASK
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        contrasena = request.form.get("contrasena", "")
        if usuario == "admin" and contrasena == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    mensaje = session.pop("mensaje", None)
    return render_template(
        "dashboard.html",
        ciudades=conteo_ciudades,
        referencias=referencias_seleccionadas,
        vehiculos=vehiculos,
        mensaje=mensaje
    )

@app.route("/upload", methods=["POST"])
def upload():
    global conteo_ciudades, datos_motos_original

    file = request.files.get("file")
    if not file:
        session["mensaje"] = "⚠️ No se recibió archivo."
        return redirect(url_for("dashboard"))

    try:
        df = pd.read_excel(file)
    except Exception as exc:
        session["mensaje"] = f"❌ Error leyendo Excel: {exc}"
        return redirect(url_for("dashboard"))

    df = _normalizar_columnas(df)

    # Validaciones mínimas (sin cambiar lógica)
    requeridas = ["Estado Satf", "Descr EXXIT", "COD INT"]
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        session["mensaje"] = f"⚠️ Faltan columnas requeridas: {', '.join(faltantes)}"
        return redirect(url_for("dashboard"))

    # Filtrar Estado Satf = 40
    df = df[df["Estado Satf"] == 40].copy()

    # Reserva a datetime (si existe)
    if "Reserva" in df.columns:
        df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    else:
        # Si no existe, crea columna para que el sort no falle
        df["Reserva"] = pd.NaT

    # Peso por equivalencia
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)

    datos_motos_original = df
    conteo_ciudades = df["Descr EXXIT"].astype(str).str.upper().value_counts().to_dict()
    session["mensaje"] = "✅ Archivo cargado correctamente."

    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    try:
        data = {
            "transportadora": request.form.get("transportadora", "").strip(),
            "conductor": request.form.get("conductor", "").strip(),
            "placa": request.form.get("placa", "").strip(),
            "cantidad_motos": int(request.form.get("cantidad_motos", "0")),
            "ciudades": [c.strip().upper() for c in request.form.get("ciudades", "").split(",") if c.strip()],
        }
    except Exception:
        session["mensaje"] = "❌ Datos de vehículo inválidos."
        return redirect(url_for("dashboard"))

    if not data["placa"]:
        session["mensaje"] = "⚠️ La placa es obligatoria."
        return redirect(url_for("dashboard"))

    if data["cantidad_motos"] <= 0:
        session["mensaje"] = "⚠️ La capacidad debe ser mayor a 0."
        return redirect(url_for("dashboard"))

    if not data["ciudades"]:
        session["mensaje"] = "⚠️ Debe ingresar al menos una ciudad (separadas por coma)."
        return redirect(url_for("dashboard"))

    vehiculos.append(data)
    session["mensaje"] = "✅ Vehículo registrado."
    return redirect(url_for("dashboard"))

# IMPORTANTE: esta ruta es la que tu dashboard.html está llamando.
# No toca algoritmo. Solo evita que Flask reviente con BuildError.
@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    # Si luego vuelves a usar selección de referencias, aquí va esa lógica.
    session["mensaje"] = "✅ Selección guardada."
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    global datos_motos_original

    if datos_motos_original.empty:
        session["mensaje"] = "⚠️ No hay datos cargados (sube el Excel primero)."
        return redirect(url_for("dashboard"))

    if not vehiculos:
        session["mensaje"] = "⚠️ No hay vehículos registrados."
        return redirect(url_for("dashboard"))

    df = _normalizar_columnas(datos_motos_original.copy())

    # Asegurar que existe Dirección 1 para tu regla indivisible
    if "Dirección 1" not in df.columns:
        session["mensaje"] = "⚠️ Falta la columna 'Dirección 1' (o 'Direccion 1') en el Excel."
        return redirect(url_for("dashboard"))

    pendientes = df.copy()
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        for v in vehiculos:
            capacidad_camion = int(v["cantidad_motos"])

            # Filtrar inventario del vehículo por ciudades permitidas
            mask_veh = pendientes["Descr EXXIT"].astype(str).str.upper().isin(v["ciudades"])
            posibles = pendientes[mask_veh].copy()
            if posibles.empty:
                continue

            # Orden por Reserva y Dirección 1 (más antiguo primero)
            posibles = posibles.sort_values(by=["Reserva", "Dirección 1"], ascending=[True, True])

            # Agrupar por Dirección 1: indivisible
            grupos = posibles.groupby("Dirección 1").agg(
                peso_espacio=("peso_espacio", "sum"),
                indices_originales=("peso_espacio", lambda x: list(x.index))
            ).reset_index()

            items = [{"id": i, "peso": int(row["peso_espacio"])} for i, row in grupos.iterrows()]

            # Knapsack (MISMA lógica)
            idx_grupos, peso_logrado = _knapsack_max_peso_min_items(items, capacidad_camion)

            # Regla 95% (MISMA lógica)
            if peso_logrado < capacidad_camion * 0.95:
                continue

            # Recuperar índices originales seleccionados
            indices_finales = []
            for i in idx_grupos:
                indices_finales.extend(grupos.iloc[i]["indices_originales"])

            asignado = pendientes.loc[indices_finales].copy()
            asignado = asignado.sort_values(by=["Reserva", "Dirección 1"], ascending=[True, True])

            # ---- FORMATO EXCEL (TU ESTRUCTURA) ----
            hoja = _excel_safe_sheet_name(v["placa"])

            resumen = pd.DataFrame([{
                "Transportadora": v.get("transportadora", ""),
                "Conductor": v.get("conductor", ""),
                "Placa": v.get("placa", ""),
                "Ciudad objetivo": ", ".join(v.get("ciudades", [])),
                "Capacidad (espacios)": capacidad_camion,
                "Ocupado (espacios)": peso_logrado,
                "Cantidad de Motos (filas)": len(asignado),
            }])

            resumen.to_excel(writer, sheet_name=hoja, index=False, startrow=0)

            # Asegurar columnas y exportar detalle en el orden fijo (fila 3)
            asignado = _asegurar_columnas_detalle(asignado)
            asignado[COLUMNAS_DETALLE].to_excel(writer, sheet_name=hoja, index=False, startrow=3)

            # Eliminar del inventario pendiente
            pendientes = pendientes.drop(asignado.index)

        # Hoja final NO_ASIGNADAS con la MISMA estructura de detalle
        if not pendientes.empty:
            pendientes = pendientes.sort_values(by=["Reserva", "Dirección 1"], ascending=[True, True])
            pendientes = _asegurar_columnas_detalle(pendientes)
            pendientes[COLUMNAS_DETALLE].to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="Despacho_Final.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
