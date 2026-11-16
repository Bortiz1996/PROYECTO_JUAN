import json

import requests

CODIGO_ESTACION = "0029037020"
FUENTE_ESTACIONES = "https://www.datos.gov.co/resource/hp9r-jxuu.json"
FUENTE_NIVELES = "https://www.datos.gov.co/resource/bdmn-sqnh.json"


def consultar(url, **params):
    respuesta = requests.get(url, params=params, timeout=60)
    respuesta.raise_for_status()
    return respuesta.json()


estacion = consultar(
    FUENTE_ESTACIONES,
    **{"$where": f"codigo='{CODIGO_ESTACION}'", "$limit": 1},
)
niveles = consultar(
    FUENTE_NIVELES,
    **{
        "$where": f"codigoestacion='{CODIGO_ESTACION}'",
        "$select": (
            "descripcionsensor,codigosensor,unidadmedida,count(*),"
            "min(fechaobservacion),max(fechaobservacion)"
        ),
        "$group": "descripcionsensor,codigosensor,unidadmedida",
    },
)

print("Estación en el catálogo IDEAM:")
print(json.dumps(estacion, ensure_ascii=False, indent=2))
print("\nObservaciones de nivel disponibles:")
print(json.dumps(niveles, ensure_ascii=False, indent=2))
if estacion and not niveles:
    print(
        "\nEl IDEAM reconoce la estación, pero esta fuente pública no contiene "
        "observaciones de nivel para ella."
    )