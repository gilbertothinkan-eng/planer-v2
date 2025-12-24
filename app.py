from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
import io
from typing import Dict, List, Optional, Set, Tuple

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

# Referencias especiales por ciudad (para el dashboard + filtro)
referencias_seleccionadas: Dict[str, List[dict]] = {}

# Equivalencias
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
    Normaliza nombres de columnas sin cambiar lógica:
    - 'Direccion 1' -> 'Dirección 1'
    """
    if "Dirección 1" not in df.columns and "Direccion 1" in df.columns:
        df = df.rename(columns={"Direccion 1": "Dirección 1"})
    return df

def _asegurar_columnas_detalle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para que el Excel SIEMPRE salga con tu estructura fija:
    si falta alguna columna, la crea vacía.
    """
    for c in COLUMNAS_DETALLE:
        if c not in df.columns:
            df[c] = ""
    return df

def encontrar_referencia_especial(ciudad: str, cod_int) -> Optional[dict]:
    """
    Retorna el dict de referencia especial para (ciudad, cod_int) si existe.
    """
    ciudad_u = str(ciudad).strip().upper()
    cod_u = str(cod_int).strip().upper()
    if ciudad_u not in referencias_seleccionadas:
        return None
    for r in referencias_seleccionadas[ciudad_u]:
        if str(r.get("cod_int", "")).strip().upper() == cod_u:
            return r
    return None

def reconstruir_referencias_especiales(df: pd.DataFrame) -> Dict[str, List[dict]]:
    """
    Construye el acordeón:
    - por ciudad
    - COD INT con equivalencia > 1
    - cantidad, equivalencia, total
    - descripcion de ejemplo (si existe columna 'Descripcion')
    """
    refs: Dict[str, List[dict]] = {}

    if "Descr EXXIT" not in df.columns or "COD INT" not in df.columns:
        return refs

    df2 = df.copy()
    df2["CIUDAD_NORM"] = df2["Descr EXXIT"].astype(str).str.upper()
    df2["COD_INT_NORM"] = df2["COD INT"].astype(str).str.upper().str.strip()

    reporte = (
        df2.groupby(["CIUDAD_NORM", "COD_INT_NORM"])
           .size()
           .reset_index(name="Cantidad")
    )

    for _, row in reporte.iterrows():
        ciudad = row["CIUDAD_NORM"]
        cod_int_norm = row["COD_INT_NORM"]
        cant = int(row["Cantidad"])
        eq = get_equivalencia(cod_int_norm)
        if eq <= 1:
            continue

        total = cant * eq
        refs.setdefault(ciudad, [])

        # Descripción representativa si existe "Descripcion"
        descripcion_ejemplo = str(cod_int_norm)
        if "Descripcion" in df2.columns:
            sub = df2[(df2["CIUDAD_NORM"] == ciudad) & (df2["COD_INT_NORM"] == cod_int_norm)]
            if not sub.empty:
                try:
                    descripcion_ejemplo = str(sub["Descripcion"].iloc[0])
                except Exception:
                    descripcion_ejemplo = str(cod_int_norm)

        refs[ciudad].append({
            "cod_int": cod_int_norm,
            "descripcion": descripcion_ejemplo,
            "cantidad": cant,
            "equivalencia": eq,
            "total": total,
            "usar": True
        })

    # Ordenar por ciudad y por total desc (opcional, visual)
    for ciudad in refs:
        refs[ciudad] = sorted(refs[ciudad], key=lambda x: (-int(x["total"]), str(x["cod_int"])))
    refs = dict(sorted(refs.items(), key=lambda x: x[0]))

    return refs

def _knapsack_max_peso_min_items(items: List[dict], capacidad: int) -> Tuple[List[int], int]:
    """
    MISMA lógica: maximiza peso <= capacidad y desempata con menos direcciones.
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

    return render_template(
        "dashboard.html",
        ciudades=conteo_ciudades,
        referencias=referencias_seleccionadas,
        vehiculos=vehiculos,
    )

@app.route("/upload", methods=["POST"])
def upload():
    global conteo_ciudades, datos_motos_original, referencias_seleccionadas

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

    # Validaciones mínimas
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
        df["Reserva"] = pd.NaT

    # Peso por equivalencia
    df["peso_espacio"] = df["COD INT"].apply(get_equivalencia)

    datos_motos_original = df

    # Conteo ciudades
    conteo_ciudades = df["Descr EXXIT"].astype(str).str.upper().value_counts().to_dict()

    # 🔥 AQUÍ ESTABA EL “HUECO”: reconstruir referencias especiales para que se muestren
    referencias_seleccionadas = reconstruir_referencias_especiales(df)

    session["mensaje"] = "✅ Archivo cargado correctamente."
    return redirect(url_for("dashboard"))

@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    """
    Guarda 'usar' True/False según los checkboxes enviados por el dashboard.
    """
    global referencias_seleccionadas

    for ciudad, refs in referencias_seleccionadas.items():
        for r in refs:
            key = f"{ciudad}_{r['cod_int']}"
            r["usar"] = key in request.form  # si viene en el POST, queda marcado

    session["mensaje"] = "✅ Selección guardada."
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

    if "Dirección 1" not in df.columns:
        session["mensaje"] = "⚠️ Falta la columna 'Dirección 1' (o 'Direccion 1') en el Excel."
        return redirect(url_for("dashboard"))

    pendientes = df.copy()
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        for v in vehiculos:
            capacidad_camion = int(v["cantidad_motos"])

            # Filtrar por ciudades del vehículo
            mask_veh = pendientes["Descr EXXIT"].astype(str).str.upper().isin(v["ciudades"])
            posibles = pendientes[mask_veh].copy()
            if posibles.empty:
                continue

            # Orden por Reserva y Dirección 1 (más antigua primero)
            posibles = posibles.sort_values(by=["Reserva", "Dirección 1"], ascending=[True, True])

            # Agrupar por Dirección 1 (indivisible)
            grupos = posibles.groupby("Dirección 1").agg(
                peso_espacio=("peso_espacio", "sum"),
                indices_originales=("peso_espacio", lambda x: list(x.index))
            ).reset_index()

            # ✅ FILTRO DE REFERENCIAS ESPECIALES (ya existía en tu versión funcional):
            # Si el grupo contiene alguna fila con COD INT especial desmarcado, se excluye el grupo.
            grupos_validos = []
            for i, row in grupos.iterrows():
                idxs = row["indices_originales"]
                sub = posibles.loc[idxs]

                permitido = True
                for _, fila in sub.iterrows():
                    cod_int = fila.get("COD INT", "")
                    eq = get_equivalencia(cod_int)
                    if eq > 1:
                        ciudad_fila = str(fila.get("Descr EXXIT", "")).upper()
                        ref = encontrar_referencia_especial(ciudad_fila, str(cod_int).upper())
                        if ref is not None and not bool(ref.get("usar", False)):
                            permitido = False
                            break

                if permitido:
                    grupos_validos.append((i, row["peso_espacio"], row["indices_originales"], row["Dirección 1"]))

            if not grupos_validos:
                continue

            # Armamos items para knapsack solo con grupos válidos
            items = [{"id": k[0], "peso": int(k[1])} for k in grupos_validos]

            idx_grupos, peso_logrado = _knapsack_max_peso_min_items(items, capacidad_camion)

            # Regla 95% (MISMA)
            if peso_logrado < capacidad_camion * 0.95:
                continue

            # Recuperar índices originales seleccionados
            indices_finales = []
            for gid in idx_grupos:
                # buscar el tuple correspondiente a gid
                for (i, _peso, idxs, _dir) in grupos_validos:
                    if i == gid:
                        indices_finales.extend(idxs)
                        break

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

            asignado = _asegurar_columnas_detalle(asignado)
            asignado[COLUMNAS_DETALLE].to_excel(writer, sheet_name=hoja, index=False, startrow=3)

            # Eliminar del inventario pendiente
            pendientes = pendientes.drop(asignado.index)

        # Hoja final NO_ASIGNADAS con la MISMA estructura
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
