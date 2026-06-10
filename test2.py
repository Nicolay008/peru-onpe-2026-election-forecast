from curl_cffi import requests

BASE = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://resultadosegundavuelta.onpe.gob.pe/main/resumen",
    "Origin": "https://resultadosegundavuelta.onpe.gob.pe",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

REGIONES = {
    "Callao":    "070000",
    "Lima":      "140000",
    "Loreto":    "150000",
    "Lambayeque":"250000",
    "Tumbes":    "240000",
}

for region, ubigeo in REGIONES.items():
    r = requests.get(f"{BASE}/resumen-general/participantes",
        params={"idEleccion":10,"tipoFiltro":"ubigeo_nivel_01",
                "idAmbitoGeografico":1,"idUbigeoDepartamento":ubigeo},
        headers=HEADERS, impersonate="chrome124", timeout=15)
    cands = r.json().get("data", [])
    print(f"\n{region}:")
    for c in cands:
        print(f"  {c['nombreAgrupacionPolitica']}: {c['porcentajeVotosValidos']:.3f}%  ({c['totalVotosValidos']:,})")

