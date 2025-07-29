import requests

url = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
response = requests.get(url)

if response.status_code == 200:
    DISPOSABLE_DOMAINS = set(
        line.strip().lower() for line in response.text.splitlines() if line.strip()
    )
    print(f"{len(DISPOSABLE_DOMAINS)} доменов загружено.")
else:
    print("Не удалось загрузить список.")
