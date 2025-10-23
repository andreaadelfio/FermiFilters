import requests
import webbrowser

url = 'http://131.154.98.245:5000/tool'
r = requests.post(url, headers={'Content-Type': 'application/xml'}, data=open('static/andrea-adelfio_tmp/fermi_vo.xml', 'rb'))

echo = r.json()
print(echo)
print(r.status_code)
id = echo.get("id")

if r.status_code == 200:
    webbrowser.open(f"http://131.154.98.245:5000/tool?id={id}")
else:
    print("Errore nella richiesta POST")