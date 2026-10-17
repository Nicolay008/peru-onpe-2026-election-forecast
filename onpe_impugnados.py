"""
ONPE — Análisis de punto de quiebre por actas enviadas al JEE
Con 906 votos de diferencia, ¿cuántas actas impugnadas voltean el resultado?

EJECUTAR:
    python onpe_impugnados.py
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

UBIGEOS = {
    "Amazonas":"010000","Ancash":"020000","Apurímac":"030000",
    "Arequipa":"040000","Ayacucho":"050000","Cajamarca":"060000",
    "Cusco":"070000","Huancavelica":"080000","Huánuco":"090000",
    "Ica":"100000","Junín":"110000","La Libertad":"120000",
    "Lambayeque":"130000","Lima":"140000","Loreto":"150000",
    "Madre de Dios":"160000","Moquegua":"170000","Pasco":"180000",
    "Piura":"190000","Puno":"200000","San Martín":"210000",
    "Tacna":"220000","Tumbes":"230000","Callao":"240000",
    "Ucayali":"250000",
}

def get_json(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, params=params, headers=HEADERS_ONPE,
                         impersonate="chrome124", timeout=15)
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as e:
        print(f"{Fore.RED}⚠ Error: {e}")
        return {}

def obtener_id_eleccion():
    data = get_json("proceso/proceso-electoral-activo")
    return data.get("idEleccionPrincipal") or data.get("id")

def api_totales(id_eleccion, ambito=1, ubigeo=None):
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": ubigeo}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/totales", params) or {}

def api_participantes(id_eleccion, ambito=1, ubigeo=None):
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": ubigeo}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/participantes", params) or []

def votos_cands(cands):
    va = next((c["totalVotosValidos"] for c in cands if "FUERZA" in c.get("nombreAgrupacionPolitica","")), 0)
    vb = next((c["totalVotosValidos"] for c in cands if "JUNTOS" in c.get("nombreAgrupacionPolitica","")), 0)
    return va, vb

def analizar():
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  ⚖  ANÁLISIS DE PUNTO DE QUIEBRE — Actas enviadas al JEE")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'═'*65}")

    id_eleccion = obtener_id_eleccion()

    # Situación actual consolidada
    cands_nac = api_participantes(id_eleccion, ambito=1)
    cands_ext = api_participantes(id_eleccion, ambito=2)
    va_nac, vb_nac = votos_cands(cands_nac)
    va_ext, vb_ext = votos_cands(cands_ext)

    va_total = va_nac + va_ext
    vb_total = vb_nac + vb_ext
    diferencia = va_total - vb_total  # positivo = Fujimori gana

    lider = "FUJIMORI" if diferencia > 0 else "SÁNCHEZ"
    col_lider = Fore.RED if diferencia > 0 else Fore.BLUE

    print(f"\n  Estado actual (interior + exterior contado):")
    print(f"  {Fore.RED}Fujimori: {va_total:>12,}  ({va_total/(va_total+vb_total)*100:.3f}%){Style.RESET_ALL}")
    print(f"  {Fore.BLUE}Sánchez:  {vb_total:>12,}  ({vb_total/(va_total+vb_total)*100:.3f}%){Style.RESET_ALL}")
    print(f"  Diferencia: {col_lider}{abs(diferencia):,} votos → {lider} lidera{Style.RESET_ALL}")

    # ── Actas enviadas al JEE por región ────────────────────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  📋 ACTAS ENVIADAS AL JEE POR REGIÓN")
    print(f"  (ya contadas pero bajo revisión formal)")
    print(f"{'═'*65}")
    print(f"\n  {'Región':<18} {'EnvJEE':>7} {'V/acta':>7} {'Votos JEE':>10} "
          f"{'% FP':>7} {'% JP':>7} {'Neto FP':>10}")
    print(f"  {'─'*18} {'─'*7} {'─'*7} {'─'*10} {'─'*7} {'─'*7} {'─'*10}")

    total_env_jee    = 0
    total_votos_jee  = 0
    votos_jee_fp     = 0
    votos_jee_jp     = 0
    filas = []

    for region, ubigeo in UBIGEOS.items():
        tots  = api_totales(id_eleccion, ubigeo=ubigeo)
        cands = api_participantes(id_eleccion, ubigeo=ubigeo)
        if not tots or not cands:
            continue

        env_jee  = tots.get("enviadasJee", 0)
        contab   = tots.get("contabilizadas", 0)
        vv       = tots.get("totalVotosValidos", 0)
        if env_jee == 0:
            continue

        va, vb   = votos_cands(cands)
        total_v  = va + vb
        if total_v == 0 or contab == 0:
            continue

        vpa      = vv / contab
        votos_en_jee = env_jee * vpa
        pct_fp   = va / total_v * 100
        pct_jp   = vb / total_v * 100
        neto_fp  = votos_en_jee * (pct_fp - pct_jp) / 100  # votos netos FP en esas actas

        total_env_jee   += env_jee
        total_votos_jee += votos_en_jee
        votos_jee_fp    += votos_en_jee * pct_fp / 100
        votos_jee_jp    += votos_en_jee * pct_jp / 100

        col = Fore.RED if pct_fp > 50 else Fore.BLUE
        filas.append((env_jee, region, env_jee, vpa, votos_en_jee,
                      pct_fp, pct_jp, neto_fp, col))

    # Ordenar por votos en JEE descendente
    filas.sort(key=lambda x: -x[2]*x[3])
    for _, region, env, vpa, v_jee, pfp, pjp, neto, col in filas:
        print(f"  {col}{region:<18}{Style.RESET_ALL} {env:>7,} {vpa:>7.0f} "
              f"{v_jee:>10,.0f} {pfp:>6.1f}% {pjp:>6.1f}% {neto:>+10,.0f}")

    # Exterior enviadas al JEE
    tots_ext = api_totales(id_eleccion, ambito=2)
    env_jee_ext = tots_ext.get("enviadasJee", 0)
    vv_ext  = tots_ext.get("totalVotosValidos", 0)
    cnt_ext = tots_ext.get("contabilizadas", 0)
    vpa_ext = vv_ext / cnt_ext if cnt_ext > 0 else 117
    v_jee_ext = env_jee_ext * vpa_ext
    pct_fp_ext = va_ext / (va_ext + vb_ext) * 100
    pct_jp_ext = vb_ext / (va_ext + vb_ext) * 100
    neto_ext = v_jee_ext * (pct_fp_ext - pct_jp_ext) / 100

    total_env_jee   += env_jee_ext
    total_votos_jee += v_jee_ext
    votos_jee_fp    += v_jee_ext * pct_fp_ext / 100
    votos_jee_jp    += v_jee_ext * pct_jp_ext / 100

    print(f"  {Fore.RED}{'✈ Exterior':<18}{Style.RESET_ALL} {env_jee_ext:>7,} {vpa_ext:>7.0f} "
          f"{v_jee_ext:>10,.0f} {pct_fp_ext:>6.1f}% {pct_jp_ext:>6.1f}% {neto_ext:>+10,.0f}")

    print(f"\n  {'─'*65}")
    print(f"  {'TOTAL':<18} {total_env_jee:>7,}         {total_votos_jee:>10,.0f}")
    print(f"  Votos JEE → FP: {votos_jee_fp:>10,.0f}  |  JP: {votos_jee_jp:>10,.0f}")
    print(f"  Ventaja neta FP en actas JEE: {Fore.RED}{votos_jee_fp - votos_jee_jp:>+,.0f}{Style.RESET_ALL}")

    # ── Punto de quiebre ────────────────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  🎯 PUNTO DE QUIEBRE — ¿Qué % de anulación voltea el resultado?")
    print(f"{'═'*65}")
    print(f"\n  Diferencia actual: {col_lider}{abs(diferencia):,} votos → {lider}{Style.RESET_ALL}")
    print(f"  Total votos en actas JEE: {total_votos_jee:,.0f}")
    print(f"  Votos netos FP en actas JEE: {votos_jee_fp - votos_jee_jp:+,.0f}")

    print(f"\n  Si el JEE anula X% de actas (proporcional a cada región):")
    print(f"  {'% anulado':>10} {'Votos anulan FP':>16} {'Votos anulan JP':>16} "
          f"{'Nueva dif':>12} {'Resultado':>12}")
    print(f"  {'─'*10} {'─'*16} {'─'*16} {'─'*12} {'─'*12}")

    for pct_anul in [1, 2, 3, 5, 8, 10, 15, 20, 25, 30]:
        anulan_fp = votos_jee_fp * pct_anul / 100
        anulan_jp = votos_jee_jp * pct_anul / 100
        nueva_dif = diferencia - (anulan_fp - anulan_jp)
        if nueva_dif > 0:
            res = f"{Fore.RED}Fujimori +{nueva_dif:,.0f}{Style.RESET_ALL}"
        elif nueva_dif < 0:
            res = f"{Fore.BLUE}Sánchez  +{abs(nueva_dif):,.0f}{Style.RESET_ALL}"
        else:
            res = f"{Fore.YELLOW}EMPATE EXACTO{Style.RESET_ALL}"
        print(f"  {pct_anul:>9}% {anulan_fp:>16,.0f} {anulan_jp:>16,.0f} "
              f"{nueva_dif:>+12,.0f}  {res}")

    # Punto exacto de quiebre
    neto_jee = votos_jee_fp - votos_jee_jp
    if neto_jee != 0:
        pct_quiebre = abs(diferencia) / abs(neto_jee) * 100
        print(f"\n  {Fore.YELLOW}⚠ Punto exacto de quiebre: {pct_quiebre:.2f}% de anulación")
        print(f"     = {abs(diferencia) / (total_votos_jee/100):.2f}% del total de votos en actas JEE{Style.RESET_ALL}")

    # ── Análisis específico de Lima ──────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  🔍 ANÁLISIS ESPECÍFICO — LIMA (el grueso de los impugnados)")
    print(f"{'═'*65}")

    tots_lima  = api_totales(id_eleccion, ubigeo="140000")
    cands_lima = api_participantes(id_eleccion, ubigeo="140000")
    env_lima   = tots_lima.get("enviadasJee", 0)
    vv_lima    = tots_lima.get("totalVotosValidos", 0)
    cnt_lima   = tots_lima.get("contabilizadas", 0)
    vpa_lima   = vv_lima / cnt_lima if cnt_lima > 0 else 219
    va_lima, vb_lima = votos_cands(cands_lima)
    tot_lima   = va_lima + vb_lima
    pct_fp_lima = va_lima / tot_lima * 100
    pct_jp_lima = vb_lima / tot_lima * 100
    votos_lima_jee = env_lima * vpa_lima
    neto_lima  = votos_lima_jee * (pct_fp_lima - pct_jp_lima) / 100

    print(f"\n  Lima actas enviadas al JEE: {env_lima:,}")
    print(f"  Votos/acta Lima:            {vpa_lima:.0f}")
    print(f"  Votos en juego Lima JEE:    {votos_lima_jee:,.0f}")
    print(f"  Fujimori gana Lima:         {pct_fp_lima:.2f}%")
    print(f"  Ventaja neta FP en Lima JEE:{neto_lima:>+,.0f} votos")
    print(f"\n  Con diferencia de {abs(diferencia):,} votos:")

    for pct_anul in [1, 2, 5, 10, 15, 20]:
        anulan_fp_l = votos_lima_jee * pct_fp_lima/100 * pct_anul/100
        anulan_jp_l = votos_lima_jee * pct_jp_lima/100 * pct_anul/100
        impacto = -(anulan_fp_l - anulan_jp_l)
        nueva_dif = diferencia + impacto
        if nueva_dif > 0:
            res = f"{Fore.RED}Fujimori +{nueva_dif:,.0f}"
        else:
            res = f"{Fore.BLUE}Sánchez  +{abs(nueva_dif):,.0f}"
        print(f"    Anular {pct_anul:>2}% actas Lima JEE → impacto: {impacto:>+8,.0f}  →  {res}{Style.RESET_ALL}")

    pct_q_lima = abs(diferencia) / abs(neto_lima) * 100 if neto_lima != 0 else 0
    print(f"\n  {Fore.YELLOW}⚠ Solo con Lima: necesitan anular {pct_q_lima:.2f}% de sus actas JEE")
    print(f"     para voltear el resultado{Style.RESET_ALL}")
    print(f"\n{'═'*65}\n")

if __name__ == "__main__":
    analizar()

    