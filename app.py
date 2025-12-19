from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from collections import Counter
import os
from typing import Dict, List, Optional, Set, Tuple

app = Flask(__name__)
app.secret_key = 'gilberto_clave_super_secreta'
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

vehiculos: List[dict] = []
conteo_ciudades: Dict[str, int] = {}
datos_motos_original = pd.DataFrame()

# DICCIONARIO COMPLETO DE EQUIVALENCIAS basado en COD INT (columna AC)
equivalencias = {
    # Las del archivo actual (que detecté)
    "AK200ZW": 6,
    "ATUL RIK": 12,
    "AK250CR4 EFI": 2,
    "HIMALAYAN 452": 2,
    "HNTR 350": 2,

    # Las de tu tabla de equivalencias (imagen)
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

    # Las que aparecen en tu archivo pero no tienen equivalencia especial (asumo = 1)
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

# Para guardar qué referencias selecciona el usuario (SOLO especiales)
referencias_seleccionadas: Dict[str, List[dict]] = {}


def get_equivalencia(cod_int: str) -> int:
    """Retorna la equivalencia en espacios basada en COD INT."""
    if pd.isna(cod_int) or cod_int == "":
        return 1
    cod_int_str = str(cod_int).strip().upper()
    return equivalencias.get(cod_int_str, 1)


def es_especial(cod_int: str) -> bool:
    """Una referencia es especial si su equivalencia es mayor a 1."""
    return get_equivalencia(cod_int) > 1


def encontrar_referencia_especial(cod_int: str, ciudad: str) -> Optional[dict]:
    """Busca una referencia especial en la lista de referencias seleccionadas de una ciudad."""
    if ciudad not in referencias_seleccionadas:
        return None

    cod_int_str = str(cod_int).strip().upper()
    for r in referencias_seleccionadas[ciudad]:
        r_cod_int = str(r["cod_int"]).strip().upper()
        if r_cod_int == cod_int_str:
            return r
    return None


def _excel_safe_sheet_name(name: str) -> str:
    """Excel limita el nombre de hoja a 31 caracteres."""
    safe = (name or "SIN_PLACA").strip()
    safe = safe.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-")
    safe = safe.replace("[", "(").replace("]", ")")
    return safe[:31] if len(safe) > 31 else safe


def seleccionar_items_knapsack_menos_items(items: List[Tuple[int, int]], capacidad: int) -> Set[int]:
    """
    Knapsack 0/1:
    - items: [(item_id, peso)]
    - maximiza peso <= capacidad
    - empate: menor cantidad de items
    Retorna: set(item_id)
    """
    if capacidad <= 0 or not items:
        return set()

    # dp[c] = (peso_total, num_items, set_ids)
    dp: List[Optional[Tuple[int, int, Set[int]]]] = [None] * (capacidad + 1)
    dp[0] = (0, 0, set())

    for item_id, w in items:
        if w <= 0 or w > capacidad:
            continue
        for c in range(capacidad, w - 1, -1):
            prev = dp[c - w]
            if prev is None:
                continue
            cand_peso = prev[0] + w
            cand_num = prev[1] + 1

            cur = dp[c]
            if cur is None or cand_peso > cur[0] or (cand_peso == cur[0] and cand_num < cur[1]):
                dp[c] = (cand_peso, cand_num, prev[2] | {item_id})

    best: Optional[Tuple[int, int, Set[int]]] = None
    for c in range(capacidad, -1, -1):
        state = dp[c]
        if state is None:
            continue
        if best is None or state[0] > best[0] or (state[0] == best[0] and state[1] < best[1]):
            best = state

    return best[2] if best else set()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]
        if usuario == "admin" and contrasena == "1234":
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    # si tu template usa session['mensaje'], esto evita 500 por variable faltante
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
    global conteo_ciudades, datos_motos_original, referencias_seleccionadas
    file = request.files["file"]
    if file and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        df = pd.read_excel(filepath)

        # Filtramos solo Estado Satf = 40
        datos_motos_original = df[df["Estado Satf"] == 40].copy()

        # Conteo de ciudades (Descr EXXIT) - MANTENER
        if "Descr EXXIT" in datos_motos_original.columns:
            conteo = Counter(datos_motos_original["Descr EXXIT"].dropna().astype(str).str.upper())
            conteo_ciudades = dict(sorted(conteo.items(), key=lambda x: x[0]))

        # Construcción del reporte SOLO de referencias especiales por ciudad
        referencias_seleccionadas = {}
        if "COD INT" in datos_motos_original.columns and "Descr EXXIT" in datos_motos_original.columns:
            reporte = (
                datos_motos_original.groupby([datos_motos_original["Descr EXXIT"].astype(str).str.upper(), "COD INT"])
                .size()
                .reset_index(name="Cantidad")
            )
            for _, row in reporte.iterrows():
                ciudad = row["Descr EXXIT"]
                cod_int = row["COD INT"]
                eq = get_equivalencia(cod_int)
                if eq <= 1:
                    continue

                cant = int(row["Cantidad"])
                total = cant * eq
                referencias_seleccionadas.setdefault(ciudad, [])

                # Obtener descripción representativa para mostrar en la interfaz
                mask = (
                    (datos_motos_original["Descr EXXIT"].astype(str).str.upper() == ciudad) &
                    (datos_motos_original["COD INT"] == cod_int)
                )
                if "Descripcion" in datos_motos_original.columns and not datos_motos_original.loc[mask].empty:
                    descripcion_ejemplo = datos_motos_original.loc[mask, "Descripcion"].iloc[0]
                else:
                    descripcion_ejemplo = str(cod_int)

                referencias_seleccionadas[ciudad].append({
                    "cod_int": cod_int,
                    "descripcion": descripcion_ejemplo,
                    "cantidad": cant,
                    "equivalencia": eq,
                    "total": total,
                    "usar": True
                })

    return redirect(url_for("dashboard"))


@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    global referencias_seleccionadas

    # Actualiza solo especiales; si no está aquí, es normal y siempre se usa
    for ciudad, refs in referencias_seleccionadas.items():
        for r in refs:
            key = f"{ciudad}_{r['cod_int']}"
            r["usar"] = key in request.form

    session['mensaje'] = "✅ Selección de referencias especiales guardada correctamente"
    return redirect(url_for("dashboard"))


@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    data = {
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",") if c.strip()]
    }
    vehiculos.append(data)
    return redirect(url_for("dashboard"))


@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    """
    NUEVA LÓGICA:
    - Agrupa por Dirección 1 (NO se divide una dirección)
    - NO repite direcciones entre vehículos
    - Llena al máximo por ciudad con knapsack (empate: menos direcciones)
    - Respeta referencias especiales (usar/no usar)
    - Respeta equivalencias
    """
    if datos_motos_original.empty:
        return "<h2>No hay datos cargados aún.</h2>"

    if not vehiculos:
        return "<h2>No hay vehículos registrados.</h2>"

    df = datos_motos_original.copy()
    excel_path = os.path.join(UPLOAD_FOLDER, "Despacho_Final.xlsx")

    # Para asegurar consistencia de ciudad/dirección
    df["CIUDAD_NORM"] = df["Descr EXXIT"].astype(str).str.upper()
    df["DIR_NORM"] = df["Dirección 1"].astype(str).str.strip().str.upper()

    direcciones_usadas: Set[str] = set()   # NO repetir direcciones entr_
