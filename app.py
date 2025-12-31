from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os, io, uuid
from typing import List, Tuple

app = Flask(__name__)
app.secret_key = "gilberto_clave_super_secreta"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. USUARIOS
USUARIOS_AUTORIZADOS = {"admin": "1234", "gilberto": "akt2025", "logistica": "akt01"}

# 2. TABLA DE EQUIVALENCIAS
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

def _actualizar_estado_inventario(df, user_id):
    df.to_pickle(os.path.join(UPLOAD_FOLDER, f"{user_id}_datos.pkl"))
    conteo_det = {}
    ciudades_list = df["Descr EXXIT"].str.upper().unique()
    for c in ciudades_list:
        df_c = df[df["Descr EXXIT"].str.upper() == c]
        norm = int(len(df_c[df_c["peso_espacio"] == 1]))
        esp = int(len(df_c[df_c["peso_espacio"] > 1]))
        conteo_det[c] = {"total": norm + esp, "normales": norm, "especiales": esp}
    session["conteo_detallado"] = conteo_det
    session["ciudades_especiales"] = [c for c, v in conteo_det.items() if v["especiales"] > 0]
    refs = {}
    for (ciudad, cod), g in df.groupby([df["Descr EXXIT"].str.upper(), "COD INT"]):
        eq = get_equivalencia(cod)
        if eq > 1:
            refs.setdefault(ciudad, []).append({"cod_int": cod, "cantidad": int(len(g)), "equivalencia": eq})
    session["referencias_seleccionadas"] = refs

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user, password = request.form.get("usuario"), request.form.get("contrasena")
        if user in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[user] == password:
            session.clear()
            session["usuario"], session["user_id"] = user, str(uuid.uuid4())
            session["vehiculos"] = []
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="❌ Acceso Denegado")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html", 
                           conteo_detallado=session.get("conteo_detallado", {}),
                           referencias=session.get("referencias_seleccionadas", {}),
                           vehiculos=session.get("vehiculos", []),
                           ciudades_especiales=session.get("ciudades_especiales", []))

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    df = pd.read_excel(file)
    df = df[df["Estado Satf"] == 40].copy()
    df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)
    _actualizar_estado_inventario(df, session['user_id'])
    session["mensaje"] = "✅ Archivo analizado"
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    v_list = session.get("vehiculos", [])
    ciudades_input = [c.strip().upper() for c in request.form["ciudades"].split(",")]
    refs_ids = request.form.getlist("refs_especiales")
    resumen_visual = []
    referencias_data = session.get("referencias_seleccionadas", {})
    for ciudad, lista_refs in referencias_data.items():
        if ciudad in ciudades_input:
            for r in lista_refs:
                if f"{ciudad}_{r['cod_int']}" in refs_ids:
                    resumen_visual.append({
                        "ciudad": ciudad, "nombre": r['cod_int'],
                        "cant": r['cantidad'], "peso_total": r['cantidad'] * r['equivalencia']
                    })
    v_list.append({
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"].upper(),
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": ciudades_input,
        "modo_carga": request.form.get("modo_carga", "todas"),
        "refs_permitidas": refs_ids,
        "resumen_visual": resumen_visual,
        "procesado": False
    })
    session["vehiculos"], session.modified, session["mensaje"] = v_list, True, "✅ Vehículo agregado"
    return redirect(url_for("dashboard"))

@app.route("/editar_vehiculo", methods=["POST"])
def editar_vehiculo():
    v_list = session.get("vehiculos", [])
    indice = int(request.form.get("indice"))
    if 0 <= indice < len(v_list):
        v_list[indice]["placa"] = request.form.get("placa").upper()
        v_list[indice]["cantidad_motos"] = int(request.form.get("cantidad_motos"))
        v_list[indice]["transportadora"] = request.form.get("transportadora")
        v_list[indice]["conductor"] = request.form.get("conductor")
        v_list[indice]["ciudades"] = [c.strip().upper() for c in request.form.get("ciudades").split(",")]
        session["vehiculos"] = v_list
        session.modified = True
    return redirect(url_for("dashboard"))

@app.route("/eliminar_vehiculo/<int:indice>")
def eliminar_vehiculo(indice):
    v_list = session.get("vehiculos", [])
    if 0 <= indice < len(v_list): v_list.pop(indice)
    session["vehiculos"], session.modified = v_list, True
    return redirect(url_for("dashboard"))

@app.route("/limpiar_cola")
def limpiar_cola():
    session["vehiculos"] = []
    session.modified = True
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    df_path = os.path.join(UPLOAD_FOLDER, f"{session.get('user_id')}_datos.pkl")
    if not os.path.exists(df_path): return "Error", 400
    df_pend = pd.read_pickle(df_path)
    vehiculos_usr = session.get("vehiculos", [])
    output = io.BytesIO()
    columnas = ["Nom PV", "No Ped", "Descr", "Descr EXXIT", "Dirección 1", "Clnt Envío", "ID Prod", "Descripcion", "ID Serie", "Estado Satf", "COD INT", "Reserva"]

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for v in vehiculos_usr:
            cap, modo, permitidas = v["cantidad_motos"], v["modo_carga"], v["refs_permitidas"]
            posibles = df_pend[df_pend["Descr EXXIT"].str.upper().isin(v["ciudades"])].copy()
            posibles = posibles.sort_values(["Reserva", "Dirección 1"])
            def permitido(r):
                if modo == "normales" and r["peso_espacio"] > 1: return False
                if modo == "especiales" and r["peso_espacio"] == 1: return False
                if r["peso_espacio"] > 1:
                    return f"{r['Descr EXXIT'].upper()}_{r['COD INT']}" in permitidas
                return True
            posibles = posibles[posibles.apply(permitido, axis=1)]
            grupos = posibles.groupby("Dirección 1").agg(peso=("peso_espacio", "sum"), idxs=("peso_espacio", lambda x: list(x.index))).reset_index()
            items = [{"id": i, "peso": int(r["peso"])} for i, r in grupos.iterrows() if r["peso"] <= cap]
            ids, peso_final = _knapsack_max_peso_min_items(items, cap)
            if peso_final > 0:
                filas = []
                for gid in ids: filas.extend(grupos.iloc[gid]["idxs"])
                asignado = df_pend.loc[filas].sort_values(["Reserva", "Dirección 1"])
                hoja = _excel_safe_sheet_name(v["placa"])
                porcentaje = f"{(peso_final / cap) * 100:.1f}%"
                enc = pd.DataFrame([{
                    "Transportadora": v["transportadora"], "Conductor": v["conductor"], 
                    "Placa": v["placa"], "Capacidad": cap, "Ocupado": peso_final, "Carga %": porcentaje
                }])
                enc.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
                asignado[columnas].to_excel(writer, sheet_name=hoja, index=False, startrow=3)
                df_pend = df_pend.drop(asignado.index)
                v["procesado"] = True
        if not df_pend.empty: df_pend[columnas].to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    _actualizar_estado_inventario(df_pend, session['user_id'])
    session.modified = True
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Planeador_AKT_Gilberto.xlsx")

if __name__ == "__main__": app.run(debug=True)
