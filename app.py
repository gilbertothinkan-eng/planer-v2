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
referencias_seleccionadas = {}

def get_equivalencia(cod_int: str) -> int:
    """Retorna la equivalencia en espacios basada en COD INT."""
    if pd.isna(cod_int) or cod_int == "":
        return 1
    
    cod_int_str = str(cod_int).strip().upper()
    return equivalencias.get(cod_int_str, 1)

def es_especial(cod_int: str) -> bool:
    """Una referencia es especial si su equivalencia es mayor a 1."""
    return get_equivalencia(cod_int) > 1

def encontrar_referencia_especial(cod_int: str, ciudad: str) -> dict:
    """
    Busca una referencia especial en la lista de referencias seleccionadas de una ciudad.
    """
    print(f"DEBUG: Buscando {cod_int} en ciudad {ciudad}")
    print(f"DEBUG: Ciudades disponibles en referencias_seleccionadas: {list(referencias_seleccionadas.keys())}")
    
    if ciudad not in referencias_seleccionadas:
        print(f"DEBUG: Ciudad {ciudad} no encontrada en referencias_seleccionadas")
        return None
    
    cod_int_str = str(cod_int).strip().upper()
    print(f"DEBUG: Buscando cod_int_str='{cod_int_str}' en {len(referencias_seleccionadas[ciudad])} referencias")
    
    for r in referencias_seleccionadas[ciudad]:
        r_cod_int = str(r["cod_int"]).strip().upper()
        print(f"DEBUG: Comparando '{cod_int_str}' con '{r_cod_int}' - usar={r.get('usar', 'NO_DEFINIDO')}")
        if r_cod_int == cod_int_str:
            print(f"DEBUG: ¡ENCONTRADA! {cod_int} -> usar={r['usar']}")
            return r
    
    print(f"DEBUG: NO ENCONTRADA referencia {cod_int} en ciudad {ciudad}")
    return None

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasena = request.form["contrasena"]
        if usuario == "admin" and contrasena == "1234":
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        ciudades=conteo_ciudades,              # mantener bloque de conteo de ciudades
        referencias=referencias_seleccionadas  # BLOQUE SOLO de especiales
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
            conteo = Counter(datos_motos_original["Descr EXXIT"].dropna().str.upper())
            # ordenar por nombre para una vista consistente
            conteo_ciudades = dict(sorted(conteo.items(), key=lambda x: x[0]))

        # Construcción del reporte SOLO de referencias especiales por ciudad
        referencias_seleccionadas = {}
        if "COD INT" in datos_motos_original.columns and "Descr EXXIT" in datos_motos_original.columns:
            reporte = (
                datos_motos_original.groupby([datos_motos_original["Descr EXXIT"].str.upper(), "COD INT"])
                .size()
                .reset_index(name="Cantidad")
            )
            for _, row in reporte.iterrows():
                ciudad = row["Descr EXXIT"]
                cod_int = row["COD INT"]
                eq = get_equivalencia(cod_int)
                if eq <= 1:
                    # No es especial → NO aparece en el bloque
                    continue
                cant = int(row["Cantidad"])
                total = cant * eq
                if ciudad not in referencias_seleccionadas:
                    referencias_seleccionadas[ciudad] = []
                
                # Obtener descripción representativa para mostrar en la interfaz
                descripcion_ejemplo = datos_motos_original[
                    (datos_motos_original["Descr EXXIT"].str.upper() == ciudad) & 
                    (datos_motos_original["COD INT"] == cod_int)
                ]["Descripcion"].iloc[0] if not datos_motos_original[
                    (datos_motos_original["Descr EXXIT"].str.upper() == ciudad) & 
                    (datos_motos_original["COD INT"] == cod_int)
                ].empty else cod_int
                
                referencias_seleccionadas[ciudad].append({
                    "cod_int": cod_int,
                    "descripcion": descripcion_ejemplo,
                    "cantidad": cant,
                    "equivalencia": eq,
                    "total": total,
                    "usar": True  # por defecto seleccionadas
                })
    return redirect(url_for("dashboard"))

@app.route("/actualizar_referencias", methods=["POST"])
def actualizar_referencias():
    global referencias_seleccionadas
    print("DEBUG: Actualizando referencias especiales...")
    print(f"DEBUG: Form data recibida: {dict(request.form)}")
    
    # Actualiza solo especiales; si no está aquí, es normal y siempre se usa
    for ciudad, refs in referencias_seleccionadas.items():
        print(f"DEBUG: Procesando ciudad {ciudad}")
        for r in refs:
            key = f"{ciudad}_{r['cod_int']}"
            old_usar = r["usar"]
            r["usar"] = key in request.form
            print(f"DEBUG: {key}: {old_usar} -> {r['usar']} (key in form: {key in request.form})")
    
    print(f"DEBUG: Estado final de referencias_seleccionadas:")
    for ciudad, refs in referencias_seleccionadas.items():
        print(f"  {ciudad}:")
        for r in refs:
            print(f"    {r['cod_int']}: usar={r['usar']}")
    
    # Agregar mensaje de confirmación
    session['mensaje'] = "✅ Selección de referencias especiales guardada correctamente"
    return redirect(url_for("dashboard"))

@app.route("/registrar_vehiculo", methods=["POST"])
def registrar_vehiculo():
    data = {
        "transportadora": request.form["transportadora"],
        "conductor": request.form["conductor"],
        "placa": request.form["placa"],
        "cantidad_motos": int(request.form["cantidad_motos"]),
        "ciudades": [c.strip().upper() for c in request.form["ciudades"].split(",")]
    }
    vehiculos.append(data)
    return redirect(url_for("dashboard"))

@app.route("/generar_planeador", methods=["POST"])
def generar_planeador():
    if datos_motos_original.empty:
        return "<h2>No hay datos cargados aún.</h2>"

    df = datos_motos_original.copy()
    df["Asignado"] = False
    excel_path = os.path.join(UPLOAD_FOLDER, "Despacho_Final.xlsx")

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for vehiculo in vehiculos:
            ciudad_objetivo = vehiculo["ciudades"][0]
            capacidad = int(vehiculo["cantidad_motos"])

            filtro = (df["Descr EXXIT"].str.upper() == ciudad_objetivo.upper()) & (~df["Asignado"])
            sub_df = df[filtro].copy()
            asignado = pd.DataFrame()

            carga_actual = 0
            
            for idx, row in sub_df.iterrows():
                cod_int = row["COD INT"]
                eq = get_equivalencia(cod_int)
                especial = eq > 1

                # Lógica corregida: Si es especial, verificar si el usuario la seleccionó
                usar = True
                if especial:
                    ref_encontrada = encontrar_referencia_especial(cod_int, ciudad_objetivo.upper())
                    if ref_encontrada is not None:
                        usar = ref_encontrada["usar"]
                        print(f"DEBUG: Referencia especial {cod_int} en {ciudad_objetivo}: usar={usar}")
                    else:
                        # Si es especial pero no está en la lista de referencias, no la usar
                        usar = False
                        print(f"DEBUG: Referencia especial {cod_int} NO ENCONTRADA en {ciudad_objetivo}, NO se usará")
                        
                if not usar:
                    print(f"DEBUG: Saltando referencia {cod_int} (usar=False)")
                    continue

                if carga_actual + eq <= capacidad:
                    asignado = pd.concat([asignado, pd.DataFrame([row])], ignore_index=True)
                    df.loc[idx, "Asignado"] = True
                    carga_actual += eq

            # Encabezado de hoja
            encabezado = pd.DataFrame([{
                "Transportadora": vehiculo["transportadora"],
                "Conductor": vehiculo["conductor"],
                "Placa": vehiculo["placa"],
                "Capacidad (espacios)": capacidad,
                "Ocupado (espacios)": carga_actual,
                "Cantidad de Motos (filas)": len(asignado)
            }])

            hoja = vehiculo["placa"]
            encabezado.to_excel(writer, sheet_name=hoja, index=False, startrow=0)
            columnas_exportar = [
                "Nom PV", "No Ped", "Descr", "Descr EXXIT", "Dirección 1",
                "Clnt Envío", "ID Prod", "Descripcion", "ID Serie", "Estado Satf", "COD INT"
            ]
            if not asignado.empty:
                asignado[columnas_exportar].to_excel(writer, sheet_name=hoja, index=False, startrow=3)
            else:
                pd.DataFrame(columns=columnas_exportar).to_excel(writer, sheet_name=hoja, index=False, startrow=3)

    return send_file(excel_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
