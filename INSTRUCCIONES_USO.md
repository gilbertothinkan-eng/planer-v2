# 📋 INSTRUCCIONES DE USO - Planeador Logístico v2.0

## 🎯 FLUJO CORRECTO (IMPORTANTE)

### ✅ PASO A PASO OBLIGATORIO:

1. **Login**: admin / 1234

2. **Subir archivo Excel**
   - Selecciona tu archivo "INFORME_CK_INFRESAKT_xxxxxx.xlsx"
   - Presiona "Cargar"

3. **📍 PASO CRÍTICO - Seleccionar Referencias Especiales**
   - Aparecerán las referencias especiales detectadas (equivalencia > 1)
   - **MARCA** las que SÍ quieres incluir en el despacho
   - **DESMARCA** las que NO quieres incluir
   - **🚨 OBLIGATORIO: Presiona "💾 GUARDAR SELECCIÓN"**
   - Verás mensaje: "✅ Selección de referencias especiales guardada correctamente"

4. **Registrar Vehículos**
   - Transportadora, conductor, placa
   - Capacidad en espacios (no en cantidad de motos)
   - Ciudad objetivo

5. **Generar Planeador**
   - Presiona "Generar Excel de Despacho"
   - Se descargará "Despacho_Final.xlsx"

## ⚠️ ERRORES COMUNES

### ❌ ERROR MÁS FRECUENTE:
**Cambiar checkboxes pero NO presionar "GUARDAR SELECCIÓN"**
- **Resultado**: Referencias desmarcadas aparecen en el despacho
- **Solución**: SIEMPRE presionar "💾 GUARDAR SELECCIÓN" después de cambios

### ❌ Otros errores:
- No revisar la capacidad del vehículo (debe ser en espacios, no motos)
- Escribir mal el nombre de la ciudad
- No verificar que el archivo Excel tenga COD INT en columna AC

## 🔧 EQUIVALENCIAS CONFIGURADAS

### Referencias Especiales (ocupan más de 1 espacio):
- **AK200ZW**: 6 espacios
- **ATUL RIK**: 12 espacios  
- **AK250CR4 EFI**: 2 espacios
- **HIMALAYAN 452**: 2 espacios
- **HNTR 350**: 2 espacios
- **300AC, 300DS, 300RALLY**: 2 espacios
- **CLASSIC 350, METEOR 350**: 2 espacios
- **CONTINENTAL GT 650, INTERCEPTOR INT 650**: 2 espacios
- **GBR 450, HIMALAYAN**: 2 espacios
- **SCRAM 411, SHOTGUN 650**: 2 espacios
- **SUPER METEOR 650**: 2 espacios

### Referencias Normales (ocupan 1 espacio):
- Todas las demás (AK110NV, AK125CR4, AK125DYN, etc.)

## 📁 ARCHIVOS INCLUIDOS

- **app.py**: Versión con debug activado
- **app_clean.py**: Versión sin debug (para producción)
- **run.bat**: Script para Windows
- **run.sh**: Script para Linux/Mac

## 🚀 EJECUCIÓN

```bash
# Windows
run.bat

# Linux/Mac  
./run.sh
```

## 📞 VERIFICACIÓN

Después de generar el planeador, verifica que:
1. Las referencias desmarcadas NO aparezcan en las hojas
2. La capacidad del vehículo se respete
3. Solo se asignen motos de la ciudad objetivo

---
**Versión:** 2.0 Mejorada
**Fecha:** Septiembre 2025
**Estado:** Problema de UX solucionado