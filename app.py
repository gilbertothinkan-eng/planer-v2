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

# 3. DICCIONARIO DE ACCESORIOS (Gilberto: Agrega nuevos aquí)
DICCIONARIO_ACCESORIOS = [
    {"ref": "7700149290036", "desc": "Retrovisor Izq 100/110NV Mp", "clave": "Moto AK110NV"},
    {"ref": "7700149289948", "desc": "Retrovisor Der 100/110NV Mp", "clave": "Moto AK110NV"},
    {"ref": "7700149313384", "desc": "Retrovisor Izq AK125CH V2 Mp", "clave": "Moto AK125 CHR"},
    {"ref": "7700149313377", "desc": "Retrovisor Der AK125CH V2 Mp", "clave": "Moto AK125 CHR"},
    {"ref": "7705946260961", "desc": "Retrovisor Der CR4 MP", "clave": "Moto AK125CR4"},
    {"ref": "7701023034296", "desc": "Retrovisor Izq CR5 MP", "clave": "Moto AK125CR4"},
    {"ref": "7705946260961", "desc": "Retrovisor Der CR4 MP", "clave": "Moto AK150CR4"},
    {"ref": "7701023034296", "desc": "Retrovisor Izq CR5 MP", "clave": "Moto AK150CR4"},
    {"ref": "7701023319133", "desc": "Retrovisor Derecho 125SC MP", "clave": "Moto AK125DYN"},
    {"ref": "7701023319140", "desc": "Retrovisor Izquierdo 125SC MP", "clave": "Moto AK125DYN"},
    {"ref": "7701023319164", "desc": "Retrovisor Izq 125W MP", "clave": "Moto AK125FLEX"},
    {"ref": "7701023319157", "desc": "Retrovisor Der 125W MP", "clave": "Moto AK125FLEX"},
    {"ref": "8430358507265", "desc": "Maletero SHAD SH-29 Ac", "clave": "Moto AK125FLEX CBS MLT"},
    {"ref": "7705946843430", "desc": "Retrovisor Derecho 125NKD Mp", "clave": "Moto AK125NKD"},
    {"ref": "7701023319119", "desc": "Retrovisor Izquierdo NKD MP", "clave": "Moto AK125NKD"},
    {"ref": "7701023384834", "desc": "Retrovisor Izq BR Mp", "clave": "Moto AK125TTR"},
    {"ref": "7701023384841", "desc": "Retrovisor Der BR Mp", "clave": "Moto AK125TTR"},
    {"ref": "7701023384834", "desc": "Retrovisor Izq BR Mp", "clave": "Moto AK200TTR"},
    {"ref": "7701023384841", "desc": "Retrovisor Der BR Mp", "clave": "Moto AK200TTR"},
    {"ref": "7700149422420", "desc": "Retrovisor Izq 150DYN RX Mp", "clave": "Moto AK150DYN RX"},
    {"ref": "7700149422413", "desc": "Retrovisor Der 150DYN RX Mp", "clave": "Moto AK150DYN RX"},
    {"ref": "7700149218962", "desc": "Retrovisor IzquierdoXC15WX Mp", "clave": "Moto AK150JET"},
    {"ref": "7700149218870", "desc": "Retrovisor Derecho XC15WX Mp", "clave": "Moto AK150JET"},
    {"ref": "7700149457033", "desc": "Pintura Cupula TT 200 TA", "clave": "Moto AK200TT"},
    {"ref": "7700149453707", "desc": "Retrovisor Derecho 200DS+ Mp", "clave": "Moto AK200TT"},
    {"ref": "7700149453684", "desc": "Retrovisor Izquierdo 200DS+ Mp", "clave": "Moto AK200TT"},
    {"ref": "7700149087797", "desc": "Maletero Spartan 45 LT Ng", "clave": "Moto AK200TT Rally"},
    {"ref": "7700149087797", "desc": "Maletero Spartan 45 LT Ng", "clave": "Moto AK200TT ABS"},
    {"ref": "7700149463164", "desc": "Retrovisor Derecho 250CR4 Mp", "clave": "Moto AK250EFI"},
    {"ref": "7700149463157", "desc": "Retrovisor Izquierdo 250CR4 Mp", "clave": "Moto AK250EFI"},
    {"ref": "7700149362917", "desc": "Retrovisor Der HY450 Mp", "clave": "Moto Hima"},
    {"ref": "7700149362900", "desc": "Retrovisor Izq HY450 Mp", "clave": "Moto Hima"},
    {"ref": "7705946987202", "desc": "Visor 300DS Mp", "clave": "Moto VOGE300DS"},
    {"ref": "7705946987424", "desc": "Retrovisor Derecho 300DS Mp", "clave": "Moto VOGE300DS"},
    {"ref": "7705946987417", "desc": "Retrovisor Izquierdo 300DS Mp", "clave": "Moto VOGE300DS"},
    {"ref": "7700149256278", "desc": "Retrovisor Izq 300Rally Mp", "clave": "Moto VOGE300Rally"},
    {"ref": "7700149243223", "desc": "Hand Saver Izq 300Rally Mp", "clave": "Moto VOGE300Rally"},
    {"ref": "7700149243216", "desc": "Hand Saver Der 300Rally Mp", "clave": "Moto VOGE300Rally"},
    {"ref": "7700149213615", "desc": "Visor Cto 300Rally Mp", "clave": "Moto VOGE300Rally"},
    {"ref": "7700149213479", "desc": "Retrovisor Der 300Rally Mp", "clave": "Moto VOGE300Rally"}
]

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
    
    session["kpi_fisico"] = session.get("kpi_inv_fisico_estatico", int(len(df)))
    session["kpi_equivalente"] = int(df["peso_espacio"].sum())

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user, password = request.form.get("usuario"), request.form.get("contrasena")
        if user in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[user] == password:
            session.clear()
            session["usuario"], session["user_id"] = user, str(uuid.uuid4())
            session["vehiculos"] = []
            session["kpi_viajes"] = 0
            session["kpi_despacho_f"] = 0
            session["kpi_despacho_e"] = 0
            session["kpi_eficiencia"] = 0
            session["kpi_top5"] = {}
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
    total_e_ini = session.get("total_equivalente_inicial", 1)
    e_actual = session.get("kpi_equivalente", 0)
    equiv_porc = int((e_actual / total_e_ini) * 100) if total_e_ini > 0 else 0
    return render_template("dashboard.html", 
                           conteo_detallado=session.get("conteo_detallado", {}),
                           referencias=session.get("referencias_seleccionadas", {}),
                           vehiculos=session.get("vehiculos", []),
                           ciudades_especiales=session.get("ciudades_especiales", []),
                           eficiencia=session.get("kpi_eficiencia", 0),
                           equiv_porc=equiv_porc)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    df = pd.read_excel(file)
    df = df[df["Estado Satf"] == 40].copy()
    df["Reserva"] = pd.to_datetime(df["Reserva"], errors="coerce")
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)
    session["kpi_inv_fisico_estatico"] = int(len(df))
    session["total_equivalente_inicial"] = int(df["peso_espacio"].sum())
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
    session["kpi_viajes"] = session.get("kpi_viajes", 0) + 1
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
        v_list[indice]["modo_carga"] = request.form.get("modo_carga")
        session["vehiculos"] = v_list
        session.modified = True
    return redirect(url_for("dashboard"))

@app.route("/eliminar_vehiculo/<int:indice>")
def eliminar_vehiculo(indice):
    v_list = session.get("vehiculos", [])
    if 0 <= indice < len(v_list): 
        v_list.pop(indice)
        session["kpi_viajes"] = max(0, session.get("kpi_viajes", 0) - 1)
    session["vehiculos"], session.modified = v_list, True
    return redirect(url_for("dashboard"))

@app.route("/limpiar_cola")
def limpiar_cola():
    session["vehiculos"] = []
    session.modified = True
    return redirect(url_for("dashboard"))

@app.route("/reset_kpis")
def reset_kpis():
    session["kpi_viajes"] = 0
    session["kpi_despacho_f"] = 0
    session["kpi_despacho_e"] = 0
    session["kpi_eficiencia"] = 0
    session["kpi_top5"] = {}
    session["mensaje"] = "♻️ KPIs Reiniciados"
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    df_path = os.path.join(UPLOAD_FOLDER, f"{session.get('user_id')}_datos.pkl")
    if not os.path.exists(df_path): return "Error", 400
    df_pend = pd.read_pickle(df_path)
    vehiculos_usr = session.get("vehiculos", [])
    output = io.BytesIO()
    columnas = ["Nom PV", "No Ped", "Descr", "Descr EXXIT", "Dirección 1", "Clnt Envío", "ID Prod", "Descripcion", "ID Serie", "Estado Satf", "COD INT", "Reserva"]

    total_despacho_fisico = 0
    total_despacho_equivalente = 0
    ciudades_acumuladas = []

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
                
                # =====================================================
                # RELLENO HUMANO CONTROLADO (POST KNAPSACK)
                # =====================================================
                espacio_libre = cap - peso_final
                if espacio_libre > 0:
                    direcciones_usadas = set(asignado["Dirección 1"].unique())

                    candidatos = df_pend[
                        (~df_pend.index.isin(asignado.index)) &
                        (~df_pend["Dirección 1"].isin(direcciones_usadas)) &
                        (df_pend["peso_espacio"] == 1)
                    ].sort_values("Reserva")

                    if not candidatos.empty:
                        direccion_objetivo = candidatos.iloc[0]["Dirección 1"]

                        motos_extra = candidatos[
                            candidatos["Dirección 1"] == direccion_objetivo
                        ].head(espacio_libre)

                        if not motos_extra.empty:
                            motos_extra = motos_extra.copy()
                            motos_extra["OBSERVACION"] = "AJUSTE OPERATIVO"

                            asignado = pd.concat([asignado, motos_extra])
                            peso_final = int(asignado["peso_espacio"].sum())
                # =====================================================               
                
                
                total_despacho_fisico += len(asignado)
                total_despacho_equivalente += peso_final
                ciudades_acumuladas.extend(asignado["Descr EXXIT"].str.upper().tolist())
                
                hoja = _excel_safe_sheet_name(v["placa"])
                porcentaje = f"{(peso_final / cap) * 100:.1f}%"
                enc = pd.DataFrame([{
                    "Transportadora": v["transportadora"], "Conductor": v["conductor"], 
                    "Placa": v["placa"], "Capacidad": cap, "Ocupado": peso_final, "Carga %": porcentaje
                }])
                enc.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
                asignado[columnas].to_excel(writer, sheet_name=hoja, index=False, startrow=3)

                # --- LÓGICA DE ACCESORIOS (COLUMNA N) ---
                conteo_acc = {}
                for _, moto in asignado.iterrows():
                    desc_moto = str(moto["Descripcion"]).upper()
                    for item in DICCIONARIO_ACCESORIOS:
                        if item["clave"].upper() in desc_moto:
                            ref_a = item["ref"]
                            if ref_a not in conteo_acc:
                                conteo_acc[ref_a] = {"desc": item["desc"], "cant": 0}
                            conteo_acc[ref_a]["cant"] += 1
                
                if conteo_acc:
                    df_acc = pd.DataFrame([
                        {"Número de artículo": k, "Descripción": v_acc["desc"], "Cantidad a despachar": v_acc["cant"]}
                        for k, v_acc in conteo_acc.items()
                    ])
                    ws = writer.sheets[hoja]
                    ws.write(2, 13, "Campo de accesorios", writer.book.add_format({'bold': True, 'font_color': 'blue'}))
                    df_acc.to_excel(writer, sheet_name=hoja, index=False, startrow=3, startcol=13)

                df_pend = df_pend.drop(asignado.index, errors="ignore")
                v["procesado"] = True

        if not df_pend.empty: df_pend[columnas].to_excel(writer, sheet_name="NO_ASIGNADAS", index=False)

    session["kpi_despacho_f"] = session.get("kpi_despacho_f", 0) + total_despacho_fisico
    session["kpi_despacho_e"] = session.get("kpi_despacho_e", 0) + total_despacho_equivalente
    inv_inicial_f = session.get("kpi_inv_fisico_estatico", 0)
    if inv_inicial_f > 0:
        session["kpi_eficiencia"] = int((session["kpi_despacho_f"] / inv_inicial_f) * 100)
    
    top5_dict = dict(session.get("kpi_top5", {}))
    nuevos_conteos = Counter(ciudades_acumuladas)
    for ciudad, cant in nuevos_conteos.items():
        top5_dict[ciudad] = top5_dict.get(ciudad, 0) + cant
    session["kpi_top5"] = dict(sorted(top5_dict.items(), key=lambda x: x[1], reverse=True)[:5])

    _actualizar_estado_inventario(df_pend, session['user_id'])
    session.modified = True
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Planeador_AKT_Gilberto.xlsx")

if __name__ == "__main__": app.run(debug=True)
