from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
from typing import Dict, List, Optional, Set

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

vehiculos: List[dict] = []
conteo_ciudades: Dict[str, int] = {}
datos_motos_original = pd.DataFrame()

# ================= EQUIVALENCIAS =================
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
    "DYNAMIC RX": 1,
}

referencias_seleccionadas: Dict[str, List[dict]] = {}

# ================= HELPERS =================
def get_equivalencia(cod_int: str) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "":
        return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)


def encontrar_referencia_especial(cod_int: str, ciudad: str) -> Optional[dict]:
    ciudad = ciudad.upper()
    for r in referencias_seleccionadas.get(ciudad, []):
        if str(r["cod_int"]).strip().upper() == str(cod_int).strip().upper():
            return r
    return None


def safe_sheet_name(name: str) -> str:
    safe = str(name or "SIN_PLACA").strip()
    for ch in ['/', '\\', ':', '*', '?', '[', ']']:
        safe = safe.replace(ch, "-")
    return safe[:31] if len(safe) > 31 else (safe or "SIN_PLACA")

# ================= ROUTES =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["contrasena"] == "1234":
            session["usuario"] = "admin"
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)


@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    mensaje = session.pop("mensaje", None)
    return render_template(
        "dashboard.html",
        ciudades=conteo_ciudades,
        referencias=referencias_seleccionadas,
        vehiculos=vehiculos,
        mensaje=mensaje,
    )


@app.route("/upload", methods=["POST"])
def upload():
    global datos_motos_original, conteo_ciudades, referencias_seleccionadas
    file = request.files["file"]
    if file:
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        df = pd.read_excel(path)

        datos_motos_original = df[df["Estado Satf"] == 40].copy()

        conteo = Counter(datos_motos_original["Descr EXXIT"].astype(str).str.upper().str.strip())
        conteo_ciudades = dict(sorted(conteo.items()))

        referencias_seleccionadas = {}
        for (ciudad, cod), grp in datos_motos_original.groupby(
            [datos_motos_original["Descr EXXIT"].astype(str).str.upper().str.strip(), "COD INT"]
        ):
            eq = get_equivalencia(cod)
            if eq > 1:
                referencias_seleccionadas.setdefault(ciudad, []).append({
                    "cod_int": cod,
                    "cantidad": len(grp),
                    "equivalencia": eq,
                    "usar": True
                })

        session["mensaje"] = "✅ Archivo cargado"
    return redirect(url_for("dashboard"))


@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    vehiculos.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [request.form["ciudades"].strip().upper()],
    })
    session["mensaje"] = "✅ Vehículo registrado"
    return redirect(url_for("dashboard"))


@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    for ciudad, refs in referencias_seleccionadas.items():
        for r in refs:
            r["usar"] = f"{ciudad}_{r['cod_int']}" in request.form
    session["mensaje"] = "✅ Selección guardada"
    return redirect(url_for("dashboard"))


@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    if datos_motos_original.empty or not vehiculos:
        return redirect(url_for("dashboard"))

    df = datos_motos_original.copy()

    # FIFO: más antiguas primero
    if "Fecha Liberacion." in df.columns:
        df["Fecha Liberacion."] = pd.to_datetime(df["Fecha Liberacion."], errors="coerce")
        df = df.sort_values("Fecha Liberacion.")

    df["CIUDAD"] = df["Descr EXXIT"].astype(str).str.upper().str.strip()
    df["DIR"] = df["Dirección 1"].astype(str).str.upper().str.strip()

    direcciones_usadas: Set[str] = set()
    indices_usados: Set[int] = set()
    plan = []

    for v in vehiculos:
        ciudad = v["ciudades"][0]
        capacidad = v["cantidad_motos"]

        dfc = df[(df["CIUDAD"] == ciudad) & (~df.index.isin(indices_usados))]

        carga = 0
        idxs = []

        for direccion, grp in dfc.groupby("DIR"):
            if direccion in direcciones_usadas:
                continue

            peso_dir = 0
            for _, row in grp.iterrows():
                eq = get_equivalencia(row["COD INT"])
                if eq > 1:
                    ref = encontrar_referencia_especial(row["COD INT"], ciudad)
                    if not ref or not ref["usar"]:
                        peso_dir = -1
                        break
                peso_dir += eq

            if peso_dir <= 0:
                continue

            if carga + peso_dir <= capacidad:
                idxs.extend(grp.index.tolist())
                carga += peso_dir
                direcciones_usadas.add(direccion)

        if carga > 0:
            asignado = df.loc[idxs]
            indices_usados.update(asignado.index.tolist())
            plan.append((v, asignado, carga))

    if not plan:
        return redirect(url_for("dashboard"))

    excel_path = os.path.join(UPLOAD_FOLDER, "Despacho_Final.xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for v, asignado, carga in plan:
            encabezado = pd.DataFrame([{
                "Placa": v["placa"],
                "Ciudad": v["ciudades"][0],
                "Capacidad": v["cantidad_motos"],
                "Ocupado": carga,
                "Cantidad filas": len(asignado)
            }])
            hoja = safe_sheet_name(v["placa"])
            encabezado.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
            asignado.to_excel(writer, sheet_name=hoja, index=False, startrow=3)

    return send_file(excel_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
