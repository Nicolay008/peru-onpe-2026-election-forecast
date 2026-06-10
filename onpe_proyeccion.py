"""
ONPE — Proyección ponderada por región (sin CSV, directo de API)
Consulta directamente la API de ONPE por cada región.

EJECUTAR:
    python onpe_proyeccion.py
"""

from curl_cffi import requests
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

BASE_URL = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend"
HEADERS_ONPE = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://resultadosegundavuelta.onpe.gob.pe/main/resumen",
    "Origin":  "https://resultadosegundavuelta.onpe.gob.pe",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# Candidatos — nombres cortos para mostrar
NOM_A = "FUERZA POPULAR"
NOM_B = "JUNTOS POR EL PERÚ"

# Ubigeos verificados con F12
UBIGEOS = {
    "Amazonas":      "010000",
    "Ancash":        "020000",
    "Apurímac":      "030000",
    "Arequipa":      "040000",
    "Ayacucho":      "050000",
    "Cajamarca":     "060000",
    "Cusco":         "070000",
    "Huancavelica":  "080000",
    "Huánuco":       "090000",
    "Ica":           "100000",
    "Junín":         "110000",
    "La Libertad":   "120000",
    "Lambayeque":    "130000",
    "Lima":          "140000",
    "Loreto":        "150000",
    "Madre de Dios": "160000",
    "Moquegua":      "170000",
    "Pasco":         "180000",
    "Piura":         "190000",
    "Puno":          "200000",
    "San Martín":    "210000",
    "Tacna":         "220000",
    "Tumbes":        "230000",
    "Callao":        "240000",
    "Ucayali":       "250000",
}

# ══════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════

def get_json(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, params=params, headers=HEADERS_ONPE,
                         impersonate="chrome124", timeout=15)
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as e:
        print(f"{Fore.RED}⚠ Error {endpoint}: {e}")
        return {}

def obtener_id_eleccion():
    data = get_json("proceso/proceso-electoral-activo")
    return data.get("idEleccionPrincipal") or data.get("id")

def api_participantes(id_eleccion, ambito=1, ubigeo=None):
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": ubigeo}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/participantes", params) or []

def api_totales(id_eleccion, ambito=1, ubigeo=None):
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": ubigeo}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/totales", params) or {}

def votos_candidatos(cands):
    """Extrae votos de Fuerza Popular y Juntos por el Perú."""
    va = next((c["totalVotosValidos"] for c in cands
               if "FUERZA" in c.get("nombreAgrupacionPolitica", "")), 0)
    vb = next((c["totalVotosValidos"] for c in cands
               if "JUNTOS" in c.get("nombreAgrupacionPolitica", "")), 0)
    return va, vb

# ══════════════════════════════════════════════════════════════════════
# PROYECCIÓN
# ══════════════════════════════════════════════════════════════════════

def calcular_proyeccion():
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  🔮 PROYECCIÓN FINAL PONDERADA POR REGIÓN")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'═'*62}")

    id_eleccion = obtener_id_eleccion()
    print(f"  Proceso activo: ID {id_eleccion}\n")

    # ── Nacional e interior ──────────────────────────────────────────
    print(f"{Fore.CYAN}⏳ Obteniendo datos nacionales...")
    cands_nac   = api_participantes(id_eleccion, ambito=1)
    totales_nac = api_totales(id_eleccion, ambito=1)
    va_nac, vb_nac = votos_candidatos(cands_nac)
    av_nac  = totales_nac.get("actasContabilizadas", 0)
    cnt_nac = totales_nac.get("contabilizadas", 0)
    tot_nac = totales_nac.get("totalActas", 0)
    pen_nac = totales_nac.get("pendientesJee", 0)

    # ── Exterior ─────────────────────────────────────────────────────
    cands_ext   = api_participantes(id_eleccion, ambito=2)
    totales_ext = api_totales(id_eleccion, ambito=2)
    va_ext, vb_ext = votos_candidatos(cands_ext)
    av_ext   = totales_ext.get("actasContabilizadas", 0)
    cnt_ext  = totales_ext.get("contabilizadas", 0)
    tot_ext  = totales_ext.get("totalActas", 0)
    pen_ext  = tot_ext - cnt_ext
    vv_ext   = totales_ext.get("totalVotosValidos", 0)
    vpa_ext  = vv_ext / cnt_ext if cnt_ext > 0 else 117

    print(f"\n  {'─'*58}")
    print(f"  INTERIOR — Avance: {av_nac:.3f}%  ({cnt_nac:,} / {tot_nac:,})")
    print(f"  {NOM_A[:25]}: {va_nac:>12,}")
    print(f"  {NOM_B[:25]}: {vb_nac:>12,}")
    print(f"  Diferencia: {Fore.YELLOW}{abs(va_nac-vb_nac):,}{Style.RESET_ALL} → "
          f"{'Sánchez' if vb_nac > va_nac else 'Fujimori'}")
    print(f"\n  EXTERIOR — Avance: {av_ext:.3f}%  ({cnt_ext:,} / {tot_ext:,})")
    print(f"  {NOM_A[:25]}: {va_ext:>12,}  ({va_ext/(va_ext+vb_ext)*100:.2f}%)")
    print(f"  {NOM_B[:25]}: {vb_ext:>12,}  ({vb_ext/(va_ext+vb_ext)*100:.2f}%)")
    print(f"  Pendientes: {pen_ext:,} actas  |  vpa: {vpa_ext:.1f}")

    # ── Proyección por región ────────────────────────────────────────
    print(f"\n{Fore.CYAN}⏳ Consultando cada región directamente de la API...")
    print(f"\n  {'Región':<18} {'Av%':>6} {'Pend':>6} {'V/acta':>7} "
          f"{'FP':>10} {'JP':>10}")
    print(f"  {'─'*18} {'─'*6} {'─'*6} {'─'*7} {'─'*10} {'─'*10}")

    proy_a = va_nac
    proy_b = vb_nac

    for region, ubigeo in UBIGEOS.items():
        cands = api_participantes(id_eleccion, ubigeo=ubigeo)
        tots  = api_totales(id_eleccion, ubigeo=ubigeo)

        if region == "Cusco":
            print("\n====================")
            print("DEBUG CUSCO")
            print(tots)
            print("====================\n")

        if not cands:
            continue

        va, vb    = votos_candidatos(cands)
        total_v   = va + vb
        avance    = tots.get("actasContabilizadas", 0)
        contab    = tots.get("contabilizadas", 0)
        pend      = tots.get("pendientesJee", 0)
        vv        = tots.get("totalVotosValidos", 0)

        if pend == 0 or total_v == 0 or contab == 0:
            continue

        # Votos por acta reales de esta región
        vpa   = vv / contab if contab > 0 else 150
        pct_a = va / total_v
        pct_b = vb / total_v

        pend_v_a = pend * vpa * pct_a
        pend_v_b = pend * vpa * pct_b

        proy_a += pend_v_a
        proy_b += pend_v_b

        col = Fore.RED if pct_a > pct_b else Fore.BLUE
        print(f"  {col}{region:<18}{Style.RESET_ALL} "
              f"{avance:>5.1f}% {pend:>6,} {vpa:>7.0f} "
              f"{pend_v_a:>+10,.0f} {pend_v_b:>+10,.0f}")

    # ── Proyección exterior ──────────────────────────────────────────
    pct_ext_a = va_ext / (va_ext + vb_ext) if (va_ext + vb_ext) > 0 else 0
    pct_ext_b = vb_ext / (va_ext + vb_ext) if (va_ext + vb_ext) > 0 else 0
    pend_ext_a = pen_ext * vpa_ext * pct_ext_a
    pend_ext_b = pen_ext * vpa_ext * pct_ext_b
    proy_a += pend_ext_a
    proy_b += pend_ext_b

    """
    Aqui van los pints temporales
    """
    print("\nDEBUG EXTERIOR")
    print(f"va_ext = {va_ext:,}")
    print(f"vb_ext = {vb_ext:,}")
    print(f"pen_ext = {pen_ext:,}")
    print(f"vpa_ext = {vpa_ext:.2f}")

    pct_ext_a = va_ext / (va_ext + vb_ext)
    pct_ext_b = vb_ext / (va_ext + vb_ext)

    print(f"pct_ext_a = {pct_ext_a:.6f}")
    print(f"pct_ext_b = {pct_ext_b:.6f}")

    pend_ext_a = pen_ext * vpa_ext * pct_ext_a
    pend_ext_b = pen_ext * vpa_ext * pct_ext_b

    print(f"pend_ext_a = {pend_ext_a:,.0f}")
    print(f"pend_ext_b = {pend_ext_b:,.0f}")
    print(f"total proyectado = {pend_ext_a + pend_ext_b:,.0f}")


    """
    Aqui continua el code normal
    """

    print(f"\n  {'─'*58}")
    print(f"  {'✈ Exterior':<18} {av_ext:>5.1f}% {pen_ext:>6,} {vpa_ext:>7.0f} "
          f"{pend_ext_a:>+10,.0f} {pend_ext_b:>+10,.0f}")

    # ── Resultado final ──────────────────────────────────────────────
    total_proy = proy_a + proy_b
    pct_a_f = proy_a / total_proy * 100
    pct_b_f = proy_b / total_proy * 100
    dif = abs(proy_a - proy_b)
    ganador = "JUNTOS POR EL PERÚ" if proy_b > proy_a else "FUERZA POPULAR"
    col_gan = Fore.BLUE if proy_b > proy_a else Fore.RED

    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  📐 RESULTADO FINAL PROYECTADO")
    print(f"{'═'*62}")
    print(f"\n  {Fore.RED}{NOM_A}{Style.RESET_ALL}")
    print(f"    ≈ {proy_a:>13,.0f} votos  ({pct_a_f:.3f}%)")
    print(f"\n  {Fore.BLUE}{NOM_B}{Style.RESET_ALL}")
    print(f"    ≈ {proy_b:>13,.0f} votos  ({pct_b_f:.3f}%)")
    print(f"\n  Diferencia:  {col_gan}≈ {dif:,.0f} votos{Style.RESET_ALL}")
    print(f"  Proyectado:  {col_gan}{ganador}{Style.RESET_ALL}")

    # ── Sensibilidad exterior ────────────────────────────────────────
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  📊 SENSIBILIDAD — Si Fujimori saca X% en exterior pendiente")
    print(f"{'═'*62}")

    # Proyección base sin exterior pendiente
    base_a = proy_a - pend_ext_a
    base_b = proy_b - pend_ext_b
    votos_pend_ext_total = pen_ext * vpa_ext

    for pct_fuji in [50, 55, 58, 60, 62, 63, 65, 67, 70]:
        pct_san = 100 - pct_fuji
        va_esc = base_a + votos_pend_ext_total * (pct_fuji / 100)
        vb_esc = base_b + votos_pend_ext_total * (pct_san / 100)
        dif_esc = va_esc - vb_esc
        if dif_esc > 0:
            res = f"{Fore.RED}Fujimori +{dif_esc:>10,.0f}"
        else:
            res = f"{Fore.BLUE}Sánchez  +{abs(dif_esc):>10,.0f}"
        marca = " ← actual" if pct_fuji == round(pct_ext_a * 100) else ""
        print(f"  {pct_fuji}% Fujimori / {pct_san}% Sánchez  →  {res}{Style.RESET_ALL}{marca}")

    print(f"\n{'═'*62}\n")

if __name__ == "__main__":
    calcular_proyeccion()


