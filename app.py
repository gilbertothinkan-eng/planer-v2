from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os

app = Flask(__name__)
app.secret_key = 'gilberto_clave_super_secreta'
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

vehiculos = []
conteo_ciudades = {}
datos_motos_original = pd.DataFrame()

# =======================
# EQUIVALENCIAS
# =======================

equivalencias = {
    "AK200ZW": 6,
    "ATUL RIK": 12,
    "AK250CR4 EFI": 2,
    "HIMALAYAN 452": 2,
    "HNTR 350": 2,
    "300AC": 2,
    "300DS": 2,
    "300RALLY": 2,
    "CLASSIC 350": 2,
    "CONTINENTAL GT 650": 2,
    "GBR 450": 2,
    "HIMALAYAN": 2,
    "INTERCEPTOR INT 650": 2,
    "METEOR 350": 2,
    "METEOR 350 STELLAR": 2,
    "SCRAM 411": 2,
    "SCRAM 411 SPIRIT": 2,
    "SHOTGUN 650": 2,
    "SUPER METEOR 650": 2,
    "AK110NV EIII": 1,
    "AK125CR4 EIII": 1,
    "AK125DYN PRO+": 1,
    "AK125FLEX EIII": 1,
    "AK125NKD EIII": 1,
    "AK125T-4": 1,
    "AK125TTR EIII": 1,
    "AK150CR4": 1,
    "AK200DS+": 1,
    "AK200TTR EIII": 1,
    "DYNAMIC RX": 1
}

referencias_seleccionadas = {}

# =======================
# HELPERS
# =======================

def get_equivalencia(cod_int):
    if pd.isna(cod_int):
        return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def encontrar_referencia_especial(cod_int, ciudad):
    ciudad = ciudad.upper()
    cod_int = str(cod_int).strip().upper()
    for r in referencias_seleccionadas.get(ciudad, []):
        if str(r["cod_int"]).strip().upper() == cod_int:
            return r
    return None

# =======================
# KNAPSACK
# =======================

def seleccionar_direcciones_knapsack(items, capacidad):
    dp = [None] * (capacidad + 1)
    dp[0] = {"peso": 0, "num": 0, "ids": set()}

    for item in items:
        w = item["peso"]
        for c in range(capacidad, w - 1, -1):
            if dp[c - w] is None:
                continue
            nuevo_peso = dp[c - w]["peso"] + w
            nuevo_num = dp[c - w]["num"] + 1
            if (
                dp[c] is None or
                nuevo_peso > dp[c]["peso"] or
                (nuevo_peso == dp[c]["peso"] and nuevo_num < dp[c]["num"])
            ):
                dp[c] = {
                    "peso": nuevo_peso,
                    "num": nuevo_num,
                    "ids": dp[c - w]["ids"] | {item["id"]}
                }

    mejor = max(
        (x for x in dp if x),
        key=lambda x: (x["peso"], -x["num"]),
        default=None
    )
    return mejor["ids"] if mejor else set()

# =======================
# RUTAS
# =======================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["contrasena"] == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", ciudades=conteo_ciudades, referencias=referencias_seleccionadas)

@app.route("/upload", methods=["POST"])
def upload():
    global datos_motos_original, conteo_ciudades, referencias_seleccionadas
    file = request.files["file"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    df = pd.read_excel(path)
    df = df[df["Estado Satf"] == 40].copy()
    df["Descr EXXIT"] = df["Descr EXXIT"].str.upper()
    datos_motos_original = df

    conteo_ciudades = dict(Counter(df["Descr EXXIT"]))

    referencias_seleccionadas = {}
    reporte = df.groupby(["Descr EXXIT", "COD INT"]).size().reset_index(name="Cantidad")

    for _, r in reporte.iterrows():
        eq = get_equivalencia(r["COD INT"])
        if eq > 1:
            referencias_seleccionadas.setdefault(r["Descr EXXIT"], []).append({
                "cod_int": r["COD INT"],
                "usar": True
            })

    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    vehiculos.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [request.form["ciudades"].strip().upper()]
    })
    return redirect(url_for("dashboard"))

# =======================
# 🚀 GENERAR PLANEADOR (NUEVO)
# =======================

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    df = datos_motos_original.copy()
    excel_path = os.path.join(UPLOAD_FOLDER, "Despacho_Final.xlsx")

    direcciones_usadas = set()
    assigned_indices = set()

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for vehiculo in vehiculos:
            ciudad = vehiculo["ciudades"][0]
            capacidad = vehiculo["cantidad_motos"]

            df_ciudad = df[
                (df["Descr EXXIT"] == ciudad) &
                (~df.index.isin(assigned_indices))
            ]

            direcciones = {}
            for idx, row in df_ciudad.iterrows():
                dir_norm = str(row["Dirección 1"]).strip().upper()
                if dir_norm in direcciones_usadas:
                    continue

                eq = get_equivalencia(row["COD INT"])
                if eq > 1:
                    ref = encontrar_referencia_especial(row["COD INT"], ciudad)
                    if ref and not ref["usar"]:
                        continue

                direcciones.setdefault(dir_norm, {"peso": 0, "indices": []})
                direcciones[dir_norm]["peso"] += eq
                direcciones[dir_norm]["indices"].append(idx)

            items = []
            keys = list(direcciones.keys())
            for i, k in enumerate(keys):
                items.append({"id": i, "peso": direcciones[k]["peso"]})

            seleccion = seleccionar_direcciones_knapsack(items, capacidad)

            usados = []
            carga = 0
            for item in items:
                if item["id"] in seleccion:
                    k = keys[item["id"]]
                    direcciones_usadas.add(k)
                    usados.extend(direcciones[k]["indices"])
                    carga += direcciones[k]["peso"]

            assigned_indices.update(usados)
            asignado = df.loc[usados] if usados else pd.DataFrame()

            encabezado = pd.DataFrame([{
                "Placa": vehiculo["placa"],
                "Capacidad": capacidad,
                "Ocupado": carga,
                "Ciudad": ciudad
            }])

            hoja = vehiculo["placa"]
            encabezado.to_excel(writer, sheet_name=hoja, index=False)
            asignado.to_excel(writer, sheet_name=hoja, startrow=3, index=False)

    return send_file(excel_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
