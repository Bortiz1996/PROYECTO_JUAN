# JUAN — Nivel del río Magdalena en Calamar (Bolívar)

Tablero público y gratuito con el nivel del río Magdalena en la estación limnimétrica **CALAMAR [29037020]** del IDEAM. Los datos se actualizan desde GitHub Actions, programado diariamente para las 7:15 a. m., 12:15 p. m. y 7:15 p. m. (hora de Colombia); GitHub puede retrasar las ejecuciones programadas. Se ve bien en el celular (Streamlit).

```
├── assets/juan_icon.png               # retrato de JUAN con fondo transparente
├── assets/juan_portada.webp            # fotografía de fondo del perfil
├── scraper_ideam.py                    # descarga, limpia y combina datos
├── nivel_calamar.csv                   # histórico limpio (lo genera el scraper)
├── nivel_calamar_fuente.json           # versión del ZIP IDEAM (lo genera el scraper)
├── app.py                              # tablero Streamlit
├── requirements.txt
└── .github/workflows/actualizar_datos.yml
```

El encabezado presenta una tarjeta de perfil con portada, el retrato de JUAN, el nombre del proyecto destacado con una franja gráfica en tonos del río y el título «Nivel del río en Calamar». El icono también aparece en la pestaña del navegador.

## 1. Subir el proyecto a GitHub
1. Cree un repositorio **público** (ej. `nivel-rio-calamar`) en <   >.
2. Suba todos los archivos respetando la carpeta `.github/workflows/`.
3. *(Opcional)* Si tiene un histórico del DHIME, súbalo como `nivel_calamar.csv` con columnas `Fecha,Nivel_cm` (formato `YYYY-MM-DD`). Mejora mucho los percentiles del semáforo.
4. También puede dejar en la carpeta del proyecto exportaciones crudas CSV/XLS/XLSX de DHIME con las columnas `CodigoEstacion,NombreEstacion,Variable,Parametro,Fecha,Unidad,Valor`; el scraper las convierte a `nivel_calamar.csv`.

## 2. Activar permisos de escritura en GitHub Actions
1. En el repositorio: **Settings → Actions → General**.
2. En **Workflow permissions** marque **Read and write permissions** y pulse **Save**.
3. Vaya a la pestaña **Actions** → «Actualizar datos nivel río Calamar» → **Run workflow** para la primera carga (descarga el ZIP nacional de aproximadamente 135 MiB y crea el histórico disponible para Calamar).
4. Verifique que aparezca un commit del bot `github-actions[bot]`. A partir de ahí corre solo cada 6 horas (hora UTC; GitHub puede demorar algunos minutos).

## 3. Desplegar en Streamlit Community Cloud
1. Entre a <https://share.streamlit.io> con su cuenta de GitHub.
2. **Create app** → seleccione el repositorio, rama `main`, archivo principal `app.py`.
3. Pulse **Deploy**. Cuando termine, copie la URL pública y péguela en la variable `APP_URL` de `app.py` (activa el botón de WhatsApp).
4. Comparta el enlace con la comunidad. Cada commit del bot actualiza la app automáticamente.

> Streamlit Cloud «duerme» las apps sin visitas por unas horas; al abrir el enlace aparece un botón para despertarla (tarda segundos).

## 4. Configurar el semáforo
Edite el inicio de `app.py`:

```python
UMBRAL_AMARILLA_CM = None   # configure solo con la cota oficial PMGRD/IDEAM
UMBRAL_NARANJA_CM  = None
UMBRAL_ROJA_CM     = None
USAR_PERCENTILES_SI_FALTAN = False
```

Mientras los umbrales estén en `None`, el panel muestra la lectura sin clasificarla como normal o alerta. No use percentiles estadísticos como sustituto de cotas oficiales.

## 5. Ajustes técnicos
- **Rango válido:** `VALOR_MIN_CM` / `VALOR_MAX_CM` en `scraper_ideam.py` (por defecto 0–2000 cm).
- **Fuente principal:** [Hidrología Nacional Diaria](https://bart.ideam.gov.co/PQRS/AQTSUtils/HidrologiaNacionalDiaria.zip) del IDEAM. El scraper consulta primero sus cabeceras HTTP (`ETag`, `Last-Modified` y tamaño) y solo descarga el ZIP cuando cambió o aún no hay histórico. Extrae `NV_MEDIA_D@29037020.data` y combina la serie con datos manuales más recientes; guarda la versión consultada en `nivel_calamar_fuente.json`.
- **Visor FEWS:** el tablero consulta la serie consolidada `SeriesHM_conv.csv` de [FEWS IDEAM](https://fews.ideam.gov.co/visorfews/nacional), filtra la estación Calamar (`0029037020`) y convierte sus niveles observados de metros a centímetros. Las lecturas FEWS posteriores al histórico local también aparecen en el medidor y la gráfica, con fecha/hora y fuente identificadas. La consulta se almacena en caché por 15 minutos; las lecturas pueden ser preliminares y no son mediciones en tiempo real.
- **Fuente secundaria:** portal oficial DHIME (<https://atencionciudadano.ideam.gov.co/>), formulario **Serie de Tiempo y Frecuencia**, serie **Nivel medio diario** de la estación **CALAMAR [29037020]**. Si la fuente nacional no está disponible, el scraper intenta Playwright headless y Chromium.
- **Ubicación:** el panel incluye un mapa interactivo del limnímetro con coordenadas del [Catálogo Nacional de Estaciones del IDEAM](https://dhime.ideam.gov.co/server/rest/services/CNE/Estaciones/MapServer/0): latitud `10.243275`, longitud `-74.915017`, altitud `8 m s. n. m.`. Son distintas de las coordenadas usadas para consultar el pronóstico meteorológico.
- **Exportaciones locales:** el scraper procesa los archivos CSV, XLS y XLSX de la carpeta del proyecto que tengan el esquema de exportación DHIME. Descarta valores mayores que `1e10` y corrige valores fuera de escala x100 (por ejemplo, `57525` → `575.25 cm`).
- **Términos DHIME:** la descarga respeta la política del portal: citar a IDEAM, no comercializar los datos y cumplir las restricciones de uso mostradas en DHIME. El workflow activa `IDEAM_DHIME_ACCEPT_TERMS=true` de acuerdo con la confirmación del responsable del proyecto.
- **Fuente terciaria:** Socrata `bdmn-sqnh` se conserva como respaldo, aunque en la consulta realizada no devolvió registros para Calamar.
- **Visualización:** el medidor vertical muestra varias siluetas de peces que cruzan el agua como si la barra fuera una mirilla. Sus especies, profundidades, desfases y ritmos de cola y aletas son distintos; se inquietan cuando el nivel baja y se asustan si supera 900 cm. La animación es ilustrativa y respeta la preferencia del navegador por movimiento reducido. La gráfica incluye una línea de referencia visual en 950 cm, que no es una cota oficial de alerta. Se puede cambiar entre los últimos 60 días, el último año, cinco años o todo el histórico, consultar las últimas 30 lecturas y descargar el CSV completo.
- **Meteorología:** Open-Meteo entrega condiciones modeladas para Calamar y precipitación horaria para las 105 subzonas del área hidrográfica Magdalena-Cauca, delimitadas por la [zonificación hidrográfica 2025 del IDEAM](https://dhime.ideam.gov.co/server/rest/services/Cartografia_Tematica/ZonificacionHidrografica/MapServer/0). El archivo `assets/subzonas_magdalena_cauca.csv` contiene un punto representativo y el área oficial de cada subzona. El panel se actualiza cada 15 minutos; pondera la lluvia de cada punto por el área de su subzona y acumula las próximas 24 horas. El resultado en mm es una profundidad media areal para toda el área hidrográfica (aprox. 270.869 km²), no la suma de milímetros entre lugares ni un volumen de agua. Atribución: [Open-Meteo](https://open-meteo.com/), licencia CC BY 4.0; el servicio gratuito es para uso no comercial.
- **Tendencia del río:** la estimación cualitativa combina las últimas lecturas diarias del nivel con la precipitación media areal pronosticada para el área hidrográfica. No es un modelo hidrológico ni una alerta oficial: la zonificación completa no delimita el aporte exacto al limnímetro y el panel no calcula escorrentía, caudales, tiempos de tránsito o descargas de embalses; la lluvia no implica un cambio inmediato en Calamar.
- **Instalación local:** ejecute `python -m playwright install chromium` después de instalar `requirements.txt`.
- **Si el scraper falla por columnas:** el dataset `57sv-p2fu` puede cambiar de esquema. Revise el log del workflow y ajuste las listas `COLS_*` al inicio del scraper.
- Prueba local: `pip install -r requirements.txt && python scraper_ideam.py && streamlit run app.py`.

## Aviso
Herramienta informativa. No reemplaza las alertas oficiales del IDEAM, la UNGRD ni del Consejo Municipal de Gestión del Riesgo.
