from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import defaultdict
import os
import io

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- VARIABLES GLOBALES ----------------
vehiculos = []
conteo_ciudades = {}
datos_motos_original = pd.DataFrame()

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

# ---------------- FUNCIONES ----------------
def get_equivalencia(cod_int):
    if pd.isna(cod_int) or str(cod_int).strip() == "":
        return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def _excel_safe_sheet_name(name):
    safe = str(name).strip() if name else "CAMION"
    for ch in ['/', '\\', ':', '*', '?', '[', ']']:
        safe = safe.replace(ch, "-")
    return safe[:31]

def knapsack(items, capacidad):
    dp = [(0, 0)] * (capacidad + 1)
    seleccion = [[] for _ in range(capacidad + 1)]

    for i, item in enumerate(items):
        w = item["peso"]
        for c in range(capacidad, w - 1, -1):
            cand = (dp[c - w][0] + w, dp[c - w][1] - 1)
            if cand > dp[c]:
                dp[c] = cand
                seleccion[c] = seleccion[c - w] + [item["id"]]

    mejor = max(range(capacidad + 1), key=lambda c: dp[c])
    return seleccion[mejor], dp[mejor][0]

# ---------------- RUTAS ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["contrasena"] == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", ciudades=conteo_ciudades, vehiculos=vehiculos)

@app.route("/upload", methods=["POST"])
def upload():
    global datos_motos_original, conteo_ciudades
    df = pd.read_excel(request.files["file"])
    df = df[df["Estado Satf"] == 40].copy()
    df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)
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
    pendientes = datos_motos_original.copy()
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        for v in vehiculos:
            posibles = pendientes[pendientes["Descr EXXIT"].str.upper().isin(v["ciudades"])].copy()
            if posibles.empty:
                continue

            posibles = posibles.sort_values(by=["Reserva", "Dirección 1"])
            grupos = posibles.groupby("Dirección 1").agg(
                peso_espacio=("peso_espacio", "sum"),
                indices=("peso_espacio", lambda x: list(x.index))
            ).reset_index()

            items = [{"id": i, "peso": r["peso_espacio"]} for i, r in grupos.iterrows()]
            idxs, peso_logrado = knapsack(items, v["cantidad_motos"])

            if peso_logrado < v["cantidad_motos"] * 0.95:
                continue

            indices_finales = []
            for i in idxs:
                indices_finales.extend(grupos.iloc[i]["indices"])

            asignado = pendientes.loc[indices_finales].copy()
            asignado = asignado.sort_values(by=["Reserva", "Dirección 1"])

            resumen = pd.DataFrame([{
                "Transportadora": v["transportadora"],
                "Conductor": v["conductor"],
                "Placa": v["placa"],
                "Ciudad objetivo": ", ".join(v["ciudades"]),
                "Capacidad (espacios)": v["cantidad_motos"],
                "Ocupado (espacios)": peso_logrado,
                "Cantidad de Motos (filas)": len(asignado)
            }])

            hoja = _excel_safe_sheet_name(v["placa"])
            resumen.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
            asignado[COLUMNAS_DETALLE].to_excel(writer, sheet_name=hoja, index=False, startrow=3)

            pendientes = pendientes.drop(asignado.index)

        if not pendientes.empty:
            pendientes = pendientes.sort_values(by=["Reserva", "Dirección 1"])
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
