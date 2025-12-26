from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
import io
from typing import Dict, List, Optional, Tuple

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# VARIABLES GLOBALES
# =========================
vehiculos: List[dict] = []
conteo_ciudades: Dict[str, int] = {}
datos_motos_original = pd.DataFrame()
referencias_seleccionadas: Dict[str, List[dict]] = {}

# =========================
# EQUIVALENCIAS
# =========================
equivalencias = {
    "AK200ZW": 6, "ATUL RIK": 12, "AK250CR4 EFI": 2, "HIMALAYAN 452": 2,
    "HNTR 350": 2, "300AC": 2, "300DS": 2, "300RALLY": 2,
    "CLASSIC 350": 2, "CONTINENTAL GT 650": 2, "GBR 450": 2,
    "HIMALAYAN": 2, "INTERCEPTOR INT 650": 2, "METEOR 350": 2,
    "METEOR 350 STELLAR": 2, "SCRAM 411": 2, "SCRAM 411 SPIRIT": 2,
    "SHOTGUN 650": 2, "SUPER METEOR 650": 2,
    "AK110NV EIII": 1, "AK125CR4 EIII": 1, "AK125DYN PRO+": 1,
    "AK125FLEX EIII": 1, "AK125NKD EIII": 1, "AK125T-4": 1,
    "AK125TTR EIII": 1, "AK150CR4": 1, "AK200DS+": 1,
    "AK200TTR EIII": 1, "DYNAMIC RX": 1,
}

# =========================
# FUNCIONES
# =========================
def get_equivalencia(cod_int: str) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "":
        return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def encontrar_referencia_especial(cod_int: str, ciudad: str) -> Optional[dict]:
    ciudad = ciudad.upper()
    if ciudad not in referencias_seleccionadas:
        return None
    for r in referencias_seleccionadas[ciudad]:
        if r["cod_int"] == cod_int:
            return r
    return None

def _excel_safe_sheet_name(name: str) -> str:
    safe = (name or "SIN_PLACA").replace("/", "-").replace("\\", "-")
    return safe[:31]

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int) -> Tuple[List[int], int]:
    dp = [(0, 0)] * (capacidad + 1)
    sel = [[] for _ in range(capacidad + 1)]

    for item in items:
        w = item["peso"]
        for c in range(capacidad, w - 1, -1):
            cand = (dp[c - w][0] + w, dp[c - w][1] - 1)
            if cand > dp[c]:
                dp[c] = cand
                sel[c] = sel[c - w] + [item["id"]]

    best_c = max(range(capacidad + 1), key=lambda x: dp[x])
    return sel[best_c], dp[best_c][0]

# =========================
# RUTAS
# =========================
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
    return render_template(
        "dashboard.html",
        ciudades=conteo_ciudades,
        referencias=referencias_seleccionadas,
        vehiculos=vehiculos
    )

@app.route("/upload", methods=["POST"])
def upload():
    global datos_motos_original, conteo_ciudades, referencias_seleccionadas

    df = pd.read_excel(request.files["file"])
    df = df[df["Estado Satf"] == 40].copy()
    df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)

    datos_motos_original = df
    conteo_ciudades = Counter(df["Descr EXXIT"].str.upper())

    referencias_seleccionadas = {}
    for (ciudad, cod), g in df.groupby([df["Descr EXXIT"].str.upper(), "COD INT"]):
        eq = get_equivalencia(cod)
        if eq > 1:
            referencias_seleccionadas.setdefault(ciudad, []).append({
                "cod_int": cod,
                "descripcion": g["Descripcion"].iloc[0],
                "cantidad": len(g),
                "equivalencia": eq,
                "total": len(g) * eq,
                "usar": True
            })

    return redirect(url_for("dashboard"))

@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    for ciudad, refs in referencias_seleccionadas.items():
        for r in refs:
            r["usar"] = f"{ciudad}_{r['cod_int']}" in request.form
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    vehiculos.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",")]
    })
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    df_pend = datos_motos_original.copy()
    output = io.BytesIO()

    columnas = [
        "Nom PV", "No Ped", "Descr", "Descr EXXIT", "Dirección 1",
        "Clnt Envío", "ID Prod", "Descripcion", "ID Serie",
        "Estado Satf", "COD INT", "Reserva"
    ]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for v in vehiculos:
            cap = v["cantidad_motos"]
            min_cap = int(cap * 0.90)

            posibles = df_pend[df_pend["Descr EXXIT"].str.upper().isin(v["ciudades"])].copy()
            posibles = posibles.sort_values(["Reserva", "Dirección 1"])

            def permitido(r):
                if r["peso_espacio"] <= 1:
                    return True
                ref = encontrar_referencia_especial(r["COD INT"], r["Descr EXXIT"])
                return ref and ref["usar"]

            posibles = posibles[posibles.apply(permitido, axis=1)]

            grupos = posibles.groupby("Dirección 1").agg(
                peso=("peso_espacio", "sum"),
                idxs=("peso_espacio", lambda x: list(x.index))
            ).reset_index()

            items = [{"id": i, "peso": int(r["peso"])} for i, r in grupos.iterrows() if r["peso"] <= cap]

            seleccion = []
            peso_final = 0

            for objetivo in range(cap, min_cap - 1, -1):
                ids, peso = _knapsack_max_peso_min_items(items, objetivo)
                if peso >= min_cap:
                    seleccion, peso_final = ids, peso
                    break

            if not seleccion:
                continue

            filas = []
            for gid in seleccion:
                filas.extend(grupos.iloc[gid]["idxs"])

            asignado = df_pend.loc[filas].sort_values(["Reserva", "Dirección 1"])
            hoja = _excel_safe_sheet_name(v["placa"])

            encabezado = pd.DataFrame([{
                "Transportadora": v["transportadora"],
                "Conductor": v["conductor"],
                "Placa": v["placa"],
                "Capacidad": cap,
                "Ocupado": peso_final,
                "Ocupación %": round(peso_final / cap * 100, 2)
            }])

            encabezado.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
            asignado[columnas].to_excel(writer, sheet_name=hoja, index=False, startrow=3)

            df_pend = df_pend.drop(asignado.index)

        if not df_pend.empty:
            df_pend[columnas].to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Planeador_Despacho_FINAL.xlsx")

if __name__ == "__main__":
    app.run(debug=True)
