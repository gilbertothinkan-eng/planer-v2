from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import pandas as pd
from collections import Counter
import os, io, uuid
from typing import Dict, List, Optional, Tuple

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# GESTIÓN DE USUARIOS
USUARIOS_AUTORIZADOS = {"admin": "1234", "gilberto": "akt2025", "logistica": "akt01"}

# EQUIVALENCIAS (INTACTO)
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

def get_equivalencia(cod_int: str) -> int:
    if pd.isna(cod_int) or str(cod_int).strip() == "": return 1
    return equivalencias.get(str(cod_int).strip().upper(), 1)

def encontrar_referencia_especial(cod_int: str, ciudad: str, referencias_usuario: dict) -> Optional[dict]:
    ciudad = ciudad.upper()
    if ciudad not in referencias_usuario: return None
    for r in referencias_usuario[ciudad]:
        if r["cod_int"] == cod_int: return r
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

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user, password = request.form.get("usuario"), request.form.get("contrasena")
        if user in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[user] == password:
            session.clear()
            session["usuario"], session["user_id"] = user, str(uuid.uuid4())
            session["vehiculos"], session["conteo_ciudades"], session["referencias_seleccionadas"] = [], {}, {}
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="❌ Usuario o contraseña incorrectos")
    return render_template("login.html")

@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        df_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_datos.pkl")
        if os.path.exists(df_path):
            try: os.remove(df_path)
            except: pass
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html", 
                           ciudades=session.get("conteo_ciudades", {}),
                           referencias=session.get("referencias_seleccionadas", {}),
                           vehiculos=session.get("vehiculos", []))

@app.route("/upload", methods=["POST"])
def upload():
    if "usuario" not in session: return redirect(url_for("login"))
    file = request.files["file"]
    df = pd.read_excel(file)
    df = df[df["Estado Satf"] == 40].copy()
    df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)
    df_path = os.path.join(UPLOAD_FOLDER, f"{session['user_id']}_datos.pkl")
    df.to_pickle(df_path)
    session["conteo_ciudades"] = dict(Counter(df["Descr EXXIT"].str.upper()))
    refs = {}
    for (ciudad, cod), g in df.groupby([df["Descr EXXIT"].str.upper(), "COD INT"]):
        eq = get_equivalencia(cod)
        if eq > 1:
            refs.setdefault(ciudad, []).append({
                "cod_int": cod, "descripcion": str(g["Descripcion"].iloc[0]),
                "cantidad": len(g), "equivalencia": eq, "usar": True
            })
    session["referencias_seleccionadas"], session["mensaje"] = refs, "✅ Archivo cargado correctamente"
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    v_list = session.get("vehiculos", [])
    v_list.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"].upper(),
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",")],
        "modo_carga": request.form.get("modo_carga", "todas")
    })
    session["vehiculos"], session.modified, session["mensaje"], session["limpiar_form"] = v_list, True, "✅ Vehículo registrado", True
    return redirect(url_for("dashboard"))

@app.route("/eliminar_vehiculo/<int:indice>")
def eliminar_vehiculo(indice):
    v_list = session.get("vehiculos", [])
    if 0 <= indice < len(v_list):
        v_list.pop(indice)
        session["vehiculos"], session.modified = v_list, True
    return redirect(url_for("dashboard"))

@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    refs = session.get("referencias_seleccionadas", {})
    for ciudad, items in refs.items():
        for r in items: r["usar"] = f"{ciudad}_{r['cod_int']}" in request.form
    session["referencias_seleccionadas"], session.modified, session["mensaje"] = refs, True, "✅ Preferencias guardadas"
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    user_id = session.get("user_id")
    df_path = os.path.join(UPLOAD_FOLDER, f"{user_id}_datos.pkl")
    if not os.path.exists(df_path): return "Cargue el archivo primero", 400
    df_pend = pd.read_pickle(df_path)
    vehiculos_usr, refs_usr = session.get("vehiculos", []), session.get("referencias_seleccionadas", {})
    output = io.BytesIO()
    columnas = ["Nom PV", "No Ped", "Descr", "Descr EXXIT", "Dirección 1", "Clnt Envío", "ID Prod", "Descripcion", "ID Serie", "Estado Satf", "COD INT", "Reserva"]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for v in vehiculos_usr:
            cap, modo = v["cantidad_motos"], v.get("modo_carga", "todas")
            min_cap = int(cap * 0.90)
            posibles = df_pend[df_pend["Descr EXXIT"].str.upper().isin(v["ciudades"])].copy()
            posibles = posibles.sort_values(["Reserva", "Dirección 1"])

            def permitido(r):
                es_esp = r["peso_espacio"] > 1
                if modo == "normales" and es_esp: return False
                if modo == "especiales" and not es_esp: return False
                if es_esp:
                    ref = encontrar_referencia_especial(r["COD INT"], r["Descr EXXIT"], refs_usr)
                    return ref and ref["usar"]
                return True

            posibles = posibles[posibles.apply(permitido, axis=1)]
            grupos = posibles.groupby("Dirección 1").agg(peso=("peso_espacio", "sum"), idxs=("peso_espacio", lambda x: list(x.index))).reset_index()
            items = [{"id": i, "peso": int(r["peso"])} for i, r in grupos.iterrows() if r["peso"] <= cap]

            seleccion, peso_final = [], 0
            for objetivo in range(cap, min_cap - 1, -1):
                ids, peso = _knapsack_max_peso_min_items(items, objetivo)
                if peso >= min_cap: seleccion, peso_final = ids, peso; break

            if seleccion:
                filas = []
                for gid in seleccion: filas.extend(grupos.iloc[gid]["idxs"])
                asignado = df_pend.loc[filas].sort_values(["Reserva", "Dirección 1"])
                hoja = _excel_safe_sheet_name(v["placa"])
                enc = pd.DataFrame([{"Transportadora": v["transportadora"], "Conductor": v["conductor"], "Placa": v["placa"], "Capacidad": cap, "Ocupado": peso_final, "Ocupación %": round(peso_final/cap*100, 2), "Modo": modo}])
                enc.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
                asignado[columnas].to_excel(writer, sheet_name=hoja, index=False, startrow=3)
                df_pend = df_pend.drop(asignado.index)

        if not df_pend.empty:
            df_pend[columnas].to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"Planeador_{session['usuario']}.xlsx")

if __name__ == "__main__": app.run(debug=True)
