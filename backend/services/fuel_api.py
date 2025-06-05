import requests

BASE_URL = "https://www.fueleconomy.gov/ws/rest"

HEADERS = {
    "Accept": "application/json"
}


def get_fuel_consumption_from_api(make: str, model: str, year: int):
    """
    Отримує середню витрату пального (л/100км) через API fueleconomy.gov.
    Повертає float або None, якщо дані не знайдено.
    """
    print(f" Запит до API: {year} {make} {model}")

    # Отримає список конфігурацій (vehicles)
    try:
        response = requests.get(
            f"{BASE_URL}/vehicle/menu/options",
            params={"year": year, "make": make, "model": model},
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()

        # Дістає перший vehicleId
        options = data.get("menuItem")
        if not options:
            print("Не знайдено жодної конфігурації")
            return None

        vehicle_id = options[0]["value"]
    except Exception as e:
        print(f"Помилка при отриманні ID: {e}")
        return None

    #  Отримає інформацію про авто
    try:
        response = requests.get(f"{BASE_URL}/vehicle/{vehicle_id}", headers=HEADERS)
        response.raise_for_status()
        info = response.json()

        city = info.get("city08")
        highway = info.get("highway08")

        if city and highway:
            avg_mpg = (float(city) + float(highway)) / 2
            l_per_100km = 235.2 / avg_mpg
            return round(l_per_100km, 1)
        else:
            print("Дані про витрату пального відсутні")
            return None

    except Exception as e:
        print(f"Помилка при запиті даних про авто: {e}")
        return None