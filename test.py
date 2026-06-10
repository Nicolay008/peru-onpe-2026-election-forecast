from curl_cffi import requests

url = "https://resultadosegundavuelta.onpe.gob.pe/presentacion-backend/proceso/proceso-electoral-activo"

r = requests.get(url, impersonate="chrome124", timeout=15)
print("Status:", r.status_code)
print("Respuesta:", r.text[:1000])