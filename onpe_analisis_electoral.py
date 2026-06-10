"""
╔══════════════════════════════════════════════════════════════════════╗
║     ANALIZADOR ELECTORAL ONPE — Segunda Vuelta Perú 2026            ║
║     Tendencias · Impugnadas · Predicciones · Exterior               ║
╚══════════════════════════════════════════════════════════════════════╝
pip install curl_cffi pandas tabulate colorama matplotlib
python onpe_analisis_electoral.py --intervalo 90 --sin-graficos
"""

import argparse, os, time
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from colorama import Fore, Style, init
from curl_cffi import requests
from tabulate import tabulate

init(autoreset=True)

BASE_URL  = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend"
HISTORIAL = "onpe_historial.csv"
COLOR_A   = "#E63946"
COLOR_B   = "#457B9D"

DEPARTAMENTOS = {
    "010000": "Amazonas",    "020000": "Ancash",      "030000": "Apurímac",
    "040000": "Arequipa",    "050000": "Ayacucho",    "060000": "Cajamarca",
    "240000": "Callao",      "070000": "Cusco",       "080000": "Huancavelica",
    "090000": "Huánuco",     "100000": "Ica",         "110000": "Junín",
    "120000": "La Libertad", "130000": "Lambayeque",  "140000": "Lima",
    "150000": "Loreto",      "160000": "Madre de Dios","170000": "Moquegua",
    "180000": "Pasco",       "190000": "Piura",       "200000": "Puno",
    "210000": "San Martín",  "220000": "Tacna",       "230000": "Tumbes",
    "250000": "Ucayali",
}

MACRORREGIONES = {
    "NORTE":      ["010000","060000","120000","130000","190000","210000","230000"],
    "CENTRO":     ["020000","050000","080000","090000","100000","110000","180000"],
    "SUR":        ["030000","040000","070000","170000","200000","220000"],
    "ORIENTE":    ["150000","160000","250000"],
    "LIMA METRO": ["140000","240000"],
}

MACRO_EMOJIS = {"NORTE":"🟡","CENTRO":"🟠","SUR":"🔴","ORIENTE":"🟢","LIMA METRO":"🔵"}

HEADERS_ONPE = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://resultadosegundavuelta.onpe.gob.pe/main/resumen",
    "Origin":  "https://resultadosegundavuelta.onpe.gob.pe",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# ══════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════

def get_json(endpoint, params=None, headers=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, params=params, headers=headers,
                         impersonate="chrome124", timeout=15)
        r.raise_for_status()
        return r.json().get("data", {})
    except Exception as e:
        print(f"{Fore.RED}⚠ Error {endpoint}: {e}")
        return {}

def obtener_id_eleccion():
    data = get_json("proceso/proceso-electoral-activo")
    id_ = data.get("idEleccionPrincipal") or data.get("id") or data.get("idEleccion")
    if not id_:
        raise ValueError("No se encontró proceso electoral activo.")
    return id_

def api_participantes(id_eleccion, ambito=1, ubigeo=None):
    """ambito=1 nacional, ambito=2 exterior"""
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": f"{ubigeo}"}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/participantes", params, HEADERS_ONPE) or []

def api_totales(id_eleccion, ambito=1, ubigeo=None):
    if ubigeo:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ubigeo_nivel_01",
                  "idAmbitoGeografico": 1, "idUbigeoDepartamento": f"{ubigeo}"}
    else:
        params = {"idEleccion": id_eleccion, "tipoFiltro": "ambito_geografico",
                  "idAmbitoGeografico": ambito}
    return get_json("resumen-general/totales", params, HEADERS_ONPE) or {}

# ══════════════════════════════════════════════════════════════════════
# HISTORIAL
# ══════════════════════════════════════════════════════════════════════

def guardar_snapshot(ts, avance, cands, totales):
    fila = {"timestamp": ts, "avance_pct": avance}
    for c in cands:
        key = c.get("nombreAgrupacionPolitica", c.get("nombreCandidato","?"))[:25]
        fila[f"pct_{key}"]   = c.get("porcentajeVotosValidos", 0)
        fila[f"votos_{key}"] = c.get("totalVotosValidos", 0)
    fila["impugnadas"] = totales.get("actasImpugnadas", 0)
    fila["pendientes"] = totales.get("pendientesJee", 0)
    df_new = pd.DataFrame([fila])
    if os.path.exists(HISTORIAL):
        df_out = pd.concat([pd.read_csv(HISTORIAL), df_new], ignore_index=True)
    else:
        df_out = df_new
    df_out.to_csv(HISTORIAL, index=False)
    return df_out

def cargar_historial():
    if not os.path.exists(HISTORIAL):
        return pd.DataFrame()
    df = pd.read_csv(HISTORIAL)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

# ══════════════════════════════════════════════════════════════════════
# VISUALIZACIONES TERMINAL
# ══════════════════════════════════════════════════════════════════════

def mostrar_bloque_candidatos(cands, totales, titulo):
    """Muestra un bloque de resultados — reutilizable para nacional y exterior."""
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  {titulo} — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═'*62}")
    if totales:
        av  = totales.get("actasContabilizadas", 0)
        cnt = totales.get("contabilizadas", 0)
        tot = totales.get("totalActas", 0)
        pen = totales.get("pendientesJee", 0)
        print(f"  Avance: {Fore.CYAN}{av:.3f}%{Style.RESET_ALL}  ({cnt:,} / {tot:,} actas)  Pendientes: {pen:,}")
    if cands:
        pcts = [c.get("porcentajeVotosValidos", 0) for c in cands]
        max_pct = max(pcts)
        dif = abs(pcts[0] - pcts[1]) if len(pcts) >= 2 else 0
        votos = [c.get("totalVotosValidos", 0) for c in cands]
        dif_votos = abs(votos[0] - votos[1]) if len(votos) >= 2 else 0
        for c in sorted(cands, key=lambda x: -x.get("porcentajeVotosValidos", 0)):
            pct = c.get("porcentajeVotosValidos", 0)
            vts = c.get("totalVotosValidos", 0)
            col = Fore.BLUE if pct == max_pct else Fore.RED
            barra = "█" * int(pct / 2)
            print(f"\n  {col}{c['nombreCandidato'][:40]}{Style.RESET_ALL}")
            print(f"    {col}{barra:<27}{Style.RESET_ALL} {pct:.3f}%  ({vts:,} votos)")
        print(f"\n  Diferencia: {Fore.YELLOW}{dif_votos:,} votos  ({dif:.3f}%){Style.RESET_ALL}")
    return cands, totales

def mostrar_tabla_macro(df):
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  🌎 RESUMEN POR MACRORREGIÓN")
    print(f"{'═'*62}")
    cols_v = [c for c in df.columns if c.startswith("votos_")]
    if len(cols_v) < 2:
        return
    nom_a = cols_v[0].replace("votos_","")
    nom_b = cols_v[1].replace("votos_","")
    tabla = []
    for macro, codigos in MACRORREGIONES.items():
        sub = df[df["macro"] == macro]
        if sub.empty: continue
        va = sub[cols_v[0]].sum(); vb = sub[cols_v[1]].sum()
        tot = va + vb
        pa = va/tot*100 if tot else 0; pb = vb/tot*100 if tot else 0
        lider = nom_a if pa > pb else nom_b
        col = Fore.BLUE if pa > pb else Fore.RED
        tabla.append([
            f"{MACRO_EMOJIS.get(macro,'')} {macro}",
            f"{pa:.2f}%", f"{pb:.2f}%",
            f"{col}{lider[:14]}{Style.RESET_ALL}",
            f"{abs(pa-pb):.2f}%",
            f"{sub['avance'].mean():.1f}%",
            f"{int(sub['impugnadas'].sum()):,}",
        ])
    print(tabulate(tabla,
        headers=["Macrorregión", nom_a[:13], nom_b[:13], "Lidera", "Dif.", "Avance", "Impugn."],
        tablefmt="rounded_outline"))

def mostrar_tabla_regiones(df):
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  🗺  RESULTADOS POR REGIÓN")
    print(f"{'═'*62}")
    cols_p = [c for c in df.columns if c.startswith("pct_")]
    if len(cols_p) < 2: return
    nom_a = cols_p[0].replace("pct_",""); nom_b = cols_p[1].replace("pct_","")
    tabla = []
    for _, r in df.sort_values("macro").iterrows():
        pa = r[cols_p[0]]; pb = r[cols_p[1]]; dif = pa - pb
        if abs(dif) < 1:   tend = f"{Fore.YELLOW}≈ EMPATE"
        elif dif > 0:       tend = f"{Fore.BLUE}▲ {nom_a[:10]}"
        else:               tend = f"{Fore.RED}▲ {nom_b[:10]}"
        tabla.append([
            f"{MACRO_EMOJIS.get(r['macro'],'')} {r['region']}",
            f"{pa:.2f}%", f"{pb:.2f}%", f"{abs(dif):.2f}%", tend,
            f"{r['avance']:.1f}%", f"{int(r['impugnadas']):,}",
        ])
    print(tabulate(tabla,
        headers=["Región", nom_a[:13], nom_b[:13], "Dif.", "Lidera", "Avance", "Impugn."],
        tablefmt="rounded_outline"))

def mostrar_predicciones(df):
    print(f"\n{'═'*62}")
    print(f"{Fore.YELLOW}  🔮 PREDICCIÓN — regiones con avance incompleto")
    print(f"{'═'*62}")
    cols_v = [c for c in df.columns if c.startswith("votos_")]
    cols_p = [c for c in df.columns if c.startswith("pred_")]
    if len(cols_p) < 2: return
    nom_a = cols_p[0].replace("pred_",""); nom_b = cols_p[1].replace("pred_","")
    inc = df[(df["avance"] > 10) & (df["avance"] < 99.5)].sort_values("avance")
    if inc.empty:
        print(f"  {Fore.GREEN}✓ Todas las regiones casi al 100%.")
        return
    tabla = []
    for _, r in inc.iterrows():
        va=int(r[cols_v[0]]); vb=int(r[cols_v[1]])
        pa=int(r[cols_p[0]]); pb=int(r[cols_p[1]])
        dif = pa - pb
        if abs(dif)<1000:  est=f"{Fore.YELLOW}⚖ MUY CERRADO"
        elif dif>0:         est=f"{Fore.BLUE}→ {nom_a[:10]}"
        else:               est=f"{Fore.RED}→ {nom_b[:10]}"
        tabla.append([r["region"], f"{r['avance']:.1f}%",
                      f"{va:,}", f"{vb:,}", f"≈{pa:,}", f"≈{pb:,}", est])
    print(tabulate(tabla,
        headers=["Región","Avance",f"{nom_a[:10]} act",f"{nom_b[:10]} act",
                 f"{nom_a[:10]} proy",f"{nom_b[:10]} proy","Tendencia"],
        tablefmt="rounded_outline"))

# ══════════════════════════════════════════════════════════════════════
# REGIONAL
# ══════════════════════════════════════════════════════════════════════

def construir_df_regional(id_eleccion):
    print(f"\n{Fore.CYAN}⏳ Consultando los 25 departamentos...")
    codigo_a_macro = {cod: m for m, cods in MACRORREGIONES.items() for cod in cods}
    filas = []
    for codigo, nombre in DEPARTAMENTOS.items():
        cands   = api_participantes(id_eleccion, ubigeo=codigo)
        totales = api_totales(id_eleccion, ubigeo=codigo)
        if not cands: continue
        fila = {"codigo": codigo, "region": nombre,
                "macro": codigo_a_macro.get(codigo, "Otro")}
        for c in cands:
            k = c.get("nombreAgrupacionPolitica", c.get("nombreCandidato","?"))[:20]
            fila[f"pct_{k}"]   = round(c.get("porcentajeVotosValidos", 0), 3)
            fila[f"votos_{k}"] = c.get("totalVotosValidos", 0)
        fila["actas_total"] = totales.get("totalActas", 0)
        fila["impugnadas"]  = totales.get("actasImpugnadas", 0)
        fila["pendientes"]  = totales.get("pendientesJee", 0)
        fila["avance"]      = round(totales.get("actasContabilizadas", 0), 2)
        filas.append(fila)
        print(f"  ✓ {nombre:<20} avance: {fila['avance']:6.2f}%  impugn: {fila['impugnadas']}")
    return pd.DataFrame(filas)

def calcular_prediccion(df):
    cols_v = [c for c in df.columns if c.startswith("votos_")]
    for col in cols_v:
        pred_col = col.replace("votos_","pred_")
        df[pred_col] = df.apply(
            lambda r: int(r[col]/(r["avance"]/100)) if r["avance"] > 10 else 0, axis=1)
    return df

# ══════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ══════════════════════════════════════════════════════════════════════

def graficar_todo(df_regional, historial):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(18, 14))
    fig.suptitle(f"ONPE — Segunda Vuelta Perú 2026  ·  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                 fontsize=14, fontweight="bold", color="white", y=0.98)

    cols_p_hist = [c for c in historial.columns if c.startswith("pct_")] if not historial.empty else []
    cols_v_reg  = [c for c in df_regional.columns if c.startswith("votos_")]
    nom_a = cols_p_hist[0].replace("pct_","") if len(cols_p_hist)>0 else "Candidato A"
    nom_b = cols_p_hist[1].replace("pct_","") if len(cols_p_hist)>1 else "Candidato B"

    ax1 = fig.add_subplot(2,2,1)
    ax1.set_title("📈 Evolución % votos válidos", fontsize=11, pad=8)
    if not historial.empty and len(cols_p_hist)>=2:
        ts=historial["timestamp"]; ya=historial[cols_p_hist[0]]; yb=historial[cols_p_hist[1]]
        ax1.plot(ts,ya,color=COLOR_A,linewidth=2.5,marker="o",markersize=5,label=nom_a[:25])
        ax1.plot(ts,yb,color=COLOR_B,linewidth=2.5,marker="o",markersize=5,label=nom_b[:25])
        ax1.axhline(50,color="white",linestyle="--",linewidth=1,alpha=0.4)
        ax1.annotate(f"{ya.iloc[-1]:.3f}%",xy=(ts.iloc[-1],ya.iloc[-1]),
                     xytext=(5,5),textcoords="offset points",color=COLOR_A,fontsize=9,fontweight="bold")
        ax1.annotate(f"{yb.iloc[-1]:.3f}%",xy=(ts.iloc[-1],yb.iloc[-1]),
                     xytext=(5,-12),textcoords="offset points",color=COLOR_B,fontsize=9,fontweight="bold")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.setp(ax1.xaxis.get_majorticklabels(),rotation=30,ha="right")
        ax1.set_ylabel("% votos válidos"); ax1.set_ylim(48,54)
        ax1.legend(fontsize=8); ax1.grid(axis="y",alpha=0.2)
    else:
        ax1.text(0.5,0.5,"Ejecuta varias veces\npara ver la evolución",
                 ha="center",va="center",transform=ax1.transAxes,fontsize=11,color="gray")

    ax2 = fig.add_subplot(2,2,2)
    ax2.set_title("📋 Avance del conteo", fontsize=11, pad=8)
    if not historial.empty and "avance_pct" in historial.columns:
        ts=historial["timestamp"]; av=historial["avance_pct"]
        ax2.fill_between(ts,av,alpha=0.3,color="#2ecc71")
        ax2.plot(ts,av,color="#2ecc71",linewidth=2.5,marker="o",markersize=5)
        ax2.axhline(100,color="white",linestyle="--",linewidth=1,alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.setp(ax2.xaxis.get_majorticklabels(),rotation=30,ha="right")
        ax2.set_ylabel("% actas contabilizadas"); ax2.set_ylim(0,105)
        ax2.grid(axis="y",alpha=0.2)

    ax3 = fig.add_subplot(2,2,3)
    ax3.set_title("🌎 % votos por macrorregión", fontsize=11, pad=8)
    if not df_regional.empty and len(cols_v_reg)>=2:
        macros,pcts_a,pcts_b = [],[],[]
        for macro, codigos in MACRORREGIONES.items():
            sub = df_regional[df_regional["macro"]==macro]
            if sub.empty: continue
            va=sub[cols_v_reg[0]].sum(); vb=sub[cols_v_reg[1]].sum(); tot=va+vb
            if tot==0: continue
            macros.append(f"{MACRO_EMOJIS.get(macro,'')} {macro}")
            pcts_a.append(va/tot*100); pcts_b.append(vb/tot*100)
        y=np.arange(len(macros)); h=0.35
        bars_a=ax3.barh(y+h/2,pcts_a,h,color=COLOR_A,alpha=0.85,label=nom_a[:20])
        bars_b=ax3.barh(y-h/2,pcts_b,h,color=COLOR_B,alpha=0.85,label=nom_b[:20])
        for bar,pct in zip(bars_a,pcts_a):
            ax3.text(bar.get_width()-0.5,bar.get_y()+bar.get_height()/2,
                     f"{pct:.1f}%",va="center",ha="right",fontsize=8.5,color="white",fontweight="bold")
        for bar,pct in zip(bars_b,pcts_b):
            ax3.text(bar.get_width()-0.5,bar.get_y()+bar.get_height()/2,
                     f"{pct:.1f}%",va="center",ha="right",fontsize=8.5,color="white",fontweight="bold")
        ax3.axvline(50,color="white",linestyle="--",linewidth=1.2,alpha=0.5)
        ax3.set_yticks(y); ax3.set_yticklabels(macros,fontsize=9)
        ax3.set_xlim(30,70); ax3.set_xlabel("% votos válidos")
        ax3.legend(fontsize=8,loc="lower right"); ax3.grid(axis="x",alpha=0.15)

    ax4 = fig.add_subplot(2,2,4)
    if not df_regional.empty:
        imp = df_regional[df_regional["impugnadas"]>0].sort_values("impugnadas",ascending=True).tail(12)
        if not imp.empty:
            ax4.barh(imp["region"],imp["impugnadas"],color="#f39c12",alpha=0.85)
            ax4.set_title(f"⚠ Impugnadas (Total: {int(df_regional['impugnadas'].sum()):,})",fontsize=11,pad=8)
            ax4.grid(axis="x",alpha=0.15)
        else:
            ax4.text(0.5,0.5,"✓ Sin impugnadas",ha="center",va="center",
                     transform=ax4.transAxes,fontsize=12,color="#2ecc71")

    plt.tight_layout(rect=[0,0,1,0.96])
    nombre_png = f"onpe_graficos_{datetime.now().strftime('%H%M%S')}.png"
    plt.savefig(nombre_png, dpi=130, bbox_inches="tight", facecolor="#1a1a2e")
    print(f"\n  🖼  Gráfico guardado: {nombre_png}")
    plt.show(block=False)
    plt.pause(3)
    return nombre_png

# ══════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def ejecutar_analisis(region_filtro=None, sin_graficos=False):
    print(f"\n{Fore.CYAN}{'█'*62}")
    print(f"  ONPE — Análisis Electoral Segunda Vuelta 2026")
    print(f"{'█'*62}{Style.RESET_ALL}")

    id_eleccion = obtener_id_eleccion()
    print(f"{Fore.CYAN}🔗 Proceso activo: ID {id_eleccion}{Style.RESET_ALL}")

    # Nacional (ámbito 1)
    cands_nac   = api_participantes(id_eleccion, ambito=1)
    totales_nac = api_totales(id_eleccion, ambito=1)
    mostrar_bloque_candidatos(cands_nac, totales_nac, "📊 RESULTADOS NACIONALES (sin exterior)")

    # Exterior (ámbito 2)
    cands_ext   = api_participantes(id_eleccion, ambito=2)
    totales_ext = api_totales(id_eleccion, ambito=2)
    mostrar_bloque_candidatos(cands_ext, totales_ext, "✈  VOTOS DEL EXTRANJERO")

    # Guardar historial
    ts = datetime.now().isoformat()
    avance = totales_nac.get("actasContabilizadas", 0)
    guardar_snapshot(ts, avance, cands_nac, totales_nac)

    # Regional
    df = construir_df_regional(id_eleccion)
    if df.empty:
        print(f"{Fore.RED}Sin datos regionales.")
        return

    if region_filtro:
        df = df[df["region"].str.upper() == region_filtro.upper()]

    df = calcular_prediccion(df)
    mostrar_tabla_macro(df)
    mostrar_tabla_regiones(df)
    mostrar_predicciones(df)

    csv_out = f"onpe_regional_{datetime.now().strftime('%H%M%S')}.csv"
    df.to_csv(csv_out, index=False, encoding="utf-8-sig")
    print(f"\n{Fore.GREEN}✅ {datetime.now().strftime('%H:%M:%S')}  —  datos en {csv_out}{Style.RESET_ALL}")

    if not sin_graficos:
        graficar_todo(df, cargar_historial())

# ══════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ONPE Análisis Electoral 2026")
    parser.add_argument("--intervalo",    type=int, default=0)
    parser.add_argument("--region",       type=str, default=None)
    parser.add_argument("--sin-graficos", action="store_true")
    args = parser.parse_args()

    if args.intervalo > 0:
        print(f"{Fore.CYAN}🔄 Actualizando cada {args.intervalo}s — Ctrl+C para detener")
        while True:
            try:
                ejecutar_analisis(args.region, args.sin_graficos)
                print(f"{Fore.CYAN}⏳ Siguiente actualización en {args.intervalo}s...")
                time.sleep(args.intervalo)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Detenido.")
                plt.close("all")
                break
    else:
        ejecutar_analisis(args.region, args.sin_graficos)
        input(f"\n{Fore.CYAN}Presiona Enter para salir...{Style.RESET_ALL}")
        plt.close("all")
