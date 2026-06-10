from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import time

options = Options()
# Activar logs de red
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=options)

# Visitar la página y esperar que Angular cargue los datos
print("Cargando página de ONPE...")
driver.get("https://resultadosegundavuelta.onpe.gob.pe/main/resumen")
time.sleep(8)  # Esperar que Angular haga sus llamadas

# Capturar todas las peticiones de red
logs = driver.execute_cdp_cmd("Network.enable", {})
logs = driver.get_log("performance")

# Buscar peticiones a la API
for entry in logs:
    import json
    msg = json.loads(entry["message"])["message"]
    if msg.get("method") == "Network.responseReceived":
        url = msg.get("params", {}).get("response", {}).get("url", "")
        if "presentacion-backend" in url or "candidatos" in url:
            print("✓ API encontrada:", url)

driver.quit()
