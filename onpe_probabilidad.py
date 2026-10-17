"""
ONPE — Análisis probabilístico del resultado final
¿Qué probabilidad tiene Fujimori de mantener su ventaja de 829 votos?

EJECUTAR:
    pip install scipy
    python onpe_probabilidad.py
"""

import numpy as np
from scipy import stats
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════════
# DATOS ACTUALES (al 11/06/2026 13:20)
# ══════════════════════════════════════════════════════════════════════

DIFERENCIA_ACTUAL = 829        # Fujimori lidera por estos votos
TOTAL_VOTOS_JEE   = 326_122    # Votos en actas bajo revisión JEE
VOTOS_JEE_FP      = 185_531    # Votos FP en actas JEE
VOTOS_JEE_JP      = 140_591    # Votos JP en actas JEE
NETO_FP_JEE       = 44_939     # Ventaja neta FP en actas JEE

# Lima específico
VOTOS_LIMA_JEE    = 199_513
NETO_LIMA_FP      = 53_857
ACTAS_LIMA_JEE    = 910

# ══════════════════════════════════════════════════════════════════════
# TASAS HISTÓRICAS DE ANULACIÓN JEE EN PERÚ
# ══════════════════════════════════════════════════════════════════════
# Basadas en elecciones peruanas previas:
# Proceso Electoral	Actas Totales	Actas Anuladas por JEE/JNE	% de Merma Real
#Segunda Vuelta 2021	86,488	            222	                     0.26%
#Segunda Vuelta 2016	77,307	            184	                     0.24%
#Segunda Vuelta 2011	75,559	            241	                     0.32%
# El JEE puede: validar (sin cambio), corregir (pequeño ajuste), o anular (elimina votos)

ESCENARIOS_HISTORICOS = {
    "Muy favorable JEE (Eficiencia top, error mínimo)": {
        "tasa_media": 0.0015,  # 0.15% de actas anuladas
        "tasa_std":   0.0005,
        "descripcion": "El JEE valida casi todo y corrige errores aritméticos integrando los votos"
    },
    "Histórico real conservador (Media de procesos)": {
        "tasa_media": 0.0027,  # 0.27% (Comportamiento histórico real del JNE)
        "tasa_std":   0.0008,
        "descripcion": "Tasa real registrada en las segundas vueltas del 2011 al 2021"
    },
    "Histórico con ruido técnico extremo": {
        "tasa_media": 0.0060,  # 0.60% de actas anuladas
        "tasa_std":   0.0015,
        "descripcion": "Escenario donde el JEE se pone el doble de estricto de lo normal"
    },
    "Alta conflictividad (Teórico destructivo)": {
        "tasa_media": 0.0100,  # 1.00% de actas anuladas (Techo histórico)
        "tasa_std":   0.0025,
        "descripcion": "Escenario crítico donde se descarta el 1% de las actas bajo revisión"
    },
}

N_SIMULACIONES = 100_000

# ══════════════════════════════════════════════════════════════════════
# SIMULACIÓN MONTE CARLO
# ══════════════════════════════════════════════════════════════════════

def simular_resultado(tasa_media, tasa_std, n_sim=N_SIMULACIONES):
    """
    Simula N escenarios donde el JEE anula actas con una tasa aleatoria.
    
    Supuesto clave: las anulaciones son proporcionales al voto de cada región
    (ni FP ni JP tiene ventaja en qué actas se anulan — modelo neutral).
    
    Returns: array de diferencias finales (+ = Fujimori gana, - = Sánchez gana)
    """
    # Tasa de anulación sigue distribución Beta (acotada entre 0 y 1)
    alpha = tasa_media * (tasa_media * (1 - tasa_media) / tasa_std**2 - 1)
    beta  = (1 - tasa_media) * (tasa_media * (1 - tasa_media) / tasa_std**2 - 1)
    alpha = max(alpha, 0.1)
    beta  = max(beta, 0.1)

    tasas = np.random.beta(alpha, beta, n_sim)

    # Votos anulados en cada simulación (proporcional a FP/JP en actas JEE)
    votos_anulan_fp = tasas * VOTOS_JEE_FP
    votos_anulan_jp = tasas * VOTOS_JEE_JP

    # Nueva diferencia = diferencia actual - (ventaja neta FP perdida)
    nuevas_difs = DIFERENCIA_ACTUAL - (votos_anulan_fp - votos_anulan_jp)

    return nuevas_difs, tasas

def simular_lima_sesgado(tasa_media, tasa_std, sesgo_lima=1.5, n_sim=N_SIMULACIONES):
    """
    Escenario donde Lima recibe más impugnaciones que el promedio
    (Sánchez impugna más en Lima porque FP gana ahí con fuerza).
    sesgo_lima: multiplicador de tasa para Lima (1.5 = 50% más impugnaciones en Lima)
    """
    alpha = tasa_media * (tasa_media * (1-tasa_media) / tasa_std**2 - 1)
    beta  = (1-tasa_media) * (tasa_media * (1-tasa_media) / tasa_std**2 - 1)
    alpha = max(alpha, 0.1); beta = max(beta, 0.1)

    tasas_base  = np.random.beta(alpha, beta, n_sim)
    tasas_lima  = np.minimum(tasas_base * sesgo_lima, 1.0)  # Lima más impugnada
    tasas_resto = tasas_base

    # Lima
    votos_lima_fp = tasas_lima * (VOTOS_LIMA_JEE * 0.635)
    votos_lima_jp = tasas_lima * (VOTOS_LIMA_JEE * 0.365)

    # Resto de regiones
    votos_resto_fp = tasas_resto * (VOTOS_JEE_FP - VOTOS_LIMA_JEE * 0.635)
    votos_resto_jp = tasas_resto * (VOTOS_JEE_JP - VOTOS_LIMA_JEE * 0.365)

    votos_anulan_fp = votos_lima_fp + votos_resto_fp
    votos_anulan_jp = votos_lima_jp + votos_resto_jp

    nuevas_difs = DIFERENCIA_ACTUAL - (votos_anulan_fp - votos_anulan_jp)
    return nuevas_difs

# ══════════════════════════════════════════════════════════════════════
# ANÁLISIS
# ══════════════════════════════════════════════════════════════════════

def analizar():
    np.random.seed(42)

    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  🎲 ANÁLISIS PROBABILÍSTICO — ¿Mantiene Fujimori la ventaja?")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'═'*65}")

    print(f"\n  Contexto:")
    print(f"  • Diferencia actual:        {Fore.RED}{DIFERENCIA_ACTUAL:,} votos → Fujimori{Style.RESET_ALL}")
    print(f"  • Actas bajo revisión JEE:  1,625 actas  ({TOTAL_VOTOS_JEE:,} votos)")
    print(f"  • Punto de quiebre:         anular solo {DIFERENCIA_ACTUAL/NETO_FP_JEE*100:.2f}% de actas JEE")
    print(f"  • Actas Lima bajo JEE:      {ACTAS_LIMA_JEE} actas — punto quiebre Lima: 1.54%")

    print(f"\n  Modelo: Monte Carlo con {N_SIMULACIONES:,} simulaciones")
    print(f"  Supuesto: anulaciones proporcionales al voto regional (neutral)")

    # ── Escenario 1: Distribución proporcional neutral ───────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  📊 ESCENARIO A — Anulaciones proporcionales (neutral)")
    print(f"{'═'*65}")
    print(f"\n  {'Escenario histórico':<45} {'P(FP gana)':>10} {'P(JP gana)':>10} {'Dif. media':>12}")
    print(f"  {'─'*45} {'─'*10} {'─'*10} {'─'*12}")

    resultados = {}
    for nombre, params in ESCENARIOS_HISTORICOS.items():
        difs, tasas = simular_resultado(params["tasa_media"], params["tasa_std"])
        p_fp = (difs > 0).mean() * 100
        p_jp = (difs < 0).mean() * 100
        dif_media = difs.mean()
        resultados[nombre] = {"difs": difs, "p_fp": p_fp, "p_jp": p_jp}

        col_fp = Fore.RED if p_fp > 50 else ""
        col_jp = Fore.BLUE if p_jp > 50 else ""
        print(f"  {nombre[:45]:<45} "
              f"{col_fp}{p_fp:>9.1f}%{Style.RESET_ALL} "
              f"{col_jp}{p_jp:>9.1f}%{Style.RESET_ALL} "
              f"{dif_media:>+12,.0f}")

    # ── Escenario 2: Lima más impugnada (realista) ───────────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  📊 ESCENARIO B — Lima recibe 50% más impugnaciones (realista)")
    print(f"  (JP impugna en Lima donde FP gana fuerte)")
    print(f"{'═'*65}")
    print(f"\n  {'Escenario histórico':<45} {'P(FP gana)':>10} {'P(JP gana)':>10} {'Dif. media':>12}")
    print(f"  {'─'*45} {'─'*10} {'─'*10} {'─'*12}")

    for nombre, params in ESCENARIOS_HISTORICOS.items():
        difs = simular_lima_sesgado(params["tasa_media"], params["tasa_std"], sesgo_lima=1.5)
        p_fp = (difs > 0).mean() * 100
        p_jp = (difs < 0).mean() * 100
        dif_media = difs.mean()

        col_fp = Fore.RED if p_fp > 50 else ""
        col_jp = Fore.BLUE if p_jp > 50 else ""
        print(f"  {nombre[:45]:<45} "
              f"{col_fp}{p_fp:>9.1f}%{Style.RESET_ALL} "
              f"{col_jp}{p_jp:>9.1f}%{Style.RESET_ALL} "
              f"{dif_media:>+12,.0f}")

    # ── Distribución de resultados del escenario más probable ────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  📈 DISTRIBUCIÓN DE RESULTADOS — Escenario histórico estándar")
    print(f"{'═'*65}")

    params_std = ESCENARIOS_HISTORICOS["Histórico real conservador (Media de procesos)"]
    difs_std, _ = simular_resultado(params_std["tasa_media"], params_std["tasa_std"])

    percentiles = [5, 10, 25, 50, 75, 90, 95]
    print(f"\n  Distribución de la diferencia final (+ = Fujimori, - = Sánchez):")
    print(f"  {'Percentil':>10} {'Diferencia':>12} {'Resultado':>20}")
    print(f"  {'─'*10} {'─'*12} {'─'*20}")
    for p in percentiles:
        val = np.percentile(difs_std, p)
        if val > 0:
            res = f"{Fore.RED}Fujimori +{val:,.0f}{Style.RESET_ALL}"
        else:
            res = f"{Fore.BLUE}Sánchez  +{abs(val):,.0f}{Style.RESET_ALL}"
        print(f"  {p:>9}% {val:>+12,.0f}  {res}")

    # Intervalo de confianza
    ic_95_low  = np.percentile(difs_std, 2.5)
    ic_95_high = np.percentile(difs_std, 97.5)
    print(f"\n  IC 95%: [{ic_95_low:+,.0f}  ,  {ic_95_high:+,.0f}]")

    # ── Resumen ejecutivo ────────────────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"{Fore.YELLOW}  🏆 RESUMEN EJECUTIVO")
    print(f"{'═'*65}")

    difs_hist, _ = simular_resultado(
        ESCENARIOS_HISTORICOS["Histórico real conservador (Media de procesos)"]["tasa_media"],
        ESCENARIOS_HISTORICOS["Histórico real conservador (Media de procesos)"]["tasa_std"]
    )
    difs_lima = simular_lima_sesgado(
        ESCENARIOS_HISTORICOS["Histórico real conservador (Media de procesos)"]["tasa_media"],
        ESCENARIOS_HISTORICOS["Histórico real conservador (Media de procesos)"]["tasa_std"],
        sesgo_lima=1.5
    )

    p_fp_neutral = (difs_hist > 0).mean() * 100
    p_fp_lima    = (difs_lima > 0).mean() * 100
    p_fp_prom    = (p_fp_neutral + p_fp_lima) / 2

    print(f"""
  Con 829 votos de diferencia y 1,625 actas en revisión JEE:

  Modelo neutral (anulación proporcional):
    P(Fujimori mantiene ventaja) = {Fore.RED}{p_fp_neutral:.1f}%{Style.RESET_ALL}
    P(Sánchez revierte)          = {Fore.BLUE}{100-p_fp_neutral:.1f}%{Style.RESET_ALL}

  Modelo realista (Lima más impugnada):
    P(Fujimori mantiene ventaja) = {Fore.RED}{p_fp_lima:.1f}%{Style.RESET_ALL}
    P(Sánchez revierte)          = {Fore.BLUE}{100-p_fp_lima:.1f}%{Style.RESET_ALL}

  Probabilidad ponderada final:
    {Fore.RED}P(Fujimori gana) ≈ {p_fp_prom:.1f}%{Style.RESET_ALL}
    {Fore.BLUE}P(Sánchez gana)  ≈ {100-p_fp_prom:.1f}%{Style.RESET_ALL}

  Limitaciones del modelo:
  • No modela impugnaciones estratégicas por región
  • Asume que el JEE actúa sin sesgo político
  • No incluye el factor de negociación/acuerdo entre partes
  • La diferencia de 829 votos está dentro del margen de cualquier
    corrección aritmética menor en actas con errores de suma
    """)

    print(f"{'═'*65}\n")

    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    plt.hist(difs_std, bins=100, density=True, alpha=0.6, color='#2ca02c', edgecolor='white', label='Simulaciones')
    plt.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Línea de Empate (0 votos)')
        
    mediana = np.median(difs_std)
    plt.axvline(x=mediana, color='blue', linestyle='-', linewidth=2, label=f'Mediana ({mediana:,.0f} votos)')
        
    plt.title('Distribución de Resultados Finales - Cómputo JEE / JNE - Simulación Montecarlo N= 100,000)', fontsize=14, fontweight='bold')
    plt.xlabel('Diferencia de Votos (+ = Fujimori gana, - = Sánchez gana)', fontsize=11)
    plt.ylabel('Densidad de Probabilidad', fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()
        # ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    analizar()
