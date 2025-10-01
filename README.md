# 🚚 PLANNER LOGÍSTICO MOTOS V2.0

## 📋 DESCRIPCIÓN
Sistema de planeación logística para despacho de motocicletas con control de equivalencias por COD INT.

**Desarrollado por:** Gilberto Thinkan  
**Versión:** 2.0 - COD INT Edition

---

## ⚡ INSTALACIÓN RÁPIDA

### MÉTODO 1: Automático (Recomendado)
1. Ejecuta `run.bat`
2. ¡Listo! El sistema se instala y ejecuta automáticamente

### MÉTODO 2: Manual
```cmd
pip install -r requirements.txt
python app.py
```

---

## 🔑 ACCESO AL SISTEMA

- **URL:** http://127.0.0.1:5000
- **Usuario:** admin
- **Contraseña:** 1234

---

## 📊 FUNCIONALIDADES

### ✅ **Carga de Datos**
- Importa archivos Excel (Informe de Reserva)
- Filtra automáticamente por Estado Satf = 40
- Detección automática de COD INT (columna AC)

### ✅ **Gestión de Equivalencias**
- **AK200ZW:** 6 espacios
- **ATUL RIK:** 12 espacios (TUK TUK)
- **Otros especiales:** 2 espacios c/u
- **Referencias normales:** 1 espacio

### ✅ **Control Granular**
- Selecciona qué referencias especiales incluir
- Control por ciudad y código interno
- Vista previa de capacidades

### ✅ **Optimización Inteligente**
- Asignación automática por capacidad
- Respeta equivalencias de espacio
- Maximiza eficiencia de carga

### ✅ **Exportación Excel**
- Hoja por vehículo
- Encabezados con información del conductor
- Incluye columna COD INT

---

## 🚀 GUÍA DE USO

### PASO 1: Cargar Datos
1. Clic en "Subir archivo Excel"
2. Selecciona tu Informe de Reserva (.xlsx)
3. El sistema detecta automáticamente las referencias especiales

### PASO 2: Configurar Referencias
1. Revisa la sección "Referencias especiales por ciudad"
2. **Desmarca** las referencias que NO quieras incluir
3. Clic en "Actualizar referencias especiales"

### PASO 3: Registrar Vehículos
1. Completa el formulario:
   - Transportadora
   - Conductor
   - Placa
   - **Capacidad en espacios** (no en unidades)
   - Ciudad objetivo

### PASO 4: Generar Planeador
1. Clic en "Generar Excel de Despacho"
2. Se descarga el archivo optimizado
3. ¡Listo para enviar a transportadoras!

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
planner_v2_final/
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias Python
├── run.bat               # Ejecutor automático
├── README.md             # Este archivo
├── static/
│   ├── css/style.css     # Estilos
│   └── images/           # Imágenes del sistema
├── templates/
│   ├── login.html        # Página de login
│   └── dashboard.html    # Dashboard principal
└── uploads/              # Archivos subidos (se crea automáticamente)
```

---

## 🔧 REQUISITOS TÉCNICOS

- **Python 3.7+**
- **Flask 2.3.3**
- **pandas 2.1.1**
- **openpyxl 3.1.2**

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Error: "Python no encontrado"
- Instala Python desde https://python.org
- Asegúrate de marcar "Add to PATH" durante la instalación

### Error: "pip no reconocido"
- Reinstala Python con la opción "Add to PATH"
- O usa: `python -m pip install -r requirements.txt`

### El navegador no abre
- Abre manualmente: http://127.0.0.1:5000

### Error en archivos Excel
- Verifica que el archivo tenga las columnas correctas
- Asegúrate que exista la columna "COD INT" (AC)
- Verifica que haya datos con Estado Satf = 40

---

## 📞 SOPORTE

Para dudas o mejoras, contacta con el desarrollador.

---

## 🎯 PRÓXIMAS FUNCIONALIDADES

- [ ] Integración con Google Maps para rutas
- [ ] Dashboard con métricas en tiempo real
- [ ] Sistema de usuarios y permisos
- [ ] API REST para integraciones
- [ ] Reportes históricos
- [ ] Notificaciones automáticas

---

**¡Gracias por usar el Planner Logístico Motos V2.0!** 🚀