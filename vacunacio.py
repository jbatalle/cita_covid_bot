import os
from configparser import ConfigParser
import requests
import time
import json
import re


def doit(personal_data, webhook_token):
    client = requests.session()
    client.headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 "
                      "Safari/537.36"
    }

    r = client.get("https://vacunacovid.catsalut.gencat.cat/")

    token = client.cookies.get_dict()['Queue-it-token-v3'].split("~")[1].replace("q_", "")

    r = client.get(f"https://vacunacovid.catsalut.gencat.cat/inici?qtoken={token}")

    d = {"qToken": token}
    client.headers.update({
        "authority": "frontdoornodepro.azurefd.net",
        "origin": "https://vacunacovid.catsalut.gencat.cat",
        "referer": "https://vacunacovid.catsalut.gencat.cat/",
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-ch-ua": 'Chromium";v="91", " Not;A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "accept": "*/*"
    })
    r = client.post(f"https://frontdoornodepro.azurefd.net/queue/validate", json=d)

    # do login
    client.headers.update({
        "x-queue-token": token
    })

    r = client.post(f"https://frontdoornodepro.azurefd.net/login", json=personal_data)

    # clean previous messages
    messages = get_messages(webhook_token)
    for m in messages:
        delete_message(webhook_token, m.get('uuid'))

    sms = get_code(webhook_token)
    d = {
        "cip": personal_data['documentID'],
        "token": sms,
        "qToken": token
    }
    v = client.post(f"https://frontdoornodepro.azurefd.net/login/validate", json=d)

    client.headers.update({
        "x-token": sms,
        "x-auth-token": v.json()['sessionID'],
        "apellido1": personal_data.get('surname'),
        "apellido2": personal_data.get('surname2'),
        "mail": personal_data.get('mail'),
        "cip": personal_data.get('documentID'),
        "nombre": personal_data.get('name'),
        "tel": personal_data.get('phone')
    })
    r = client.get(f"https://frontdoornodepro.azurefd.net/sf/user/system")

    for i in range(100):
        get_centers(client)
        time.sleep(10)


def get_centers(client):
    r = client.get("https://frontdoornodepro.azurefd.net/sf/centers")
    centers = r.json()
    for c in centers:
        print(f"{c['city']}-{c['centerDescription']}-{c['availableDays']}")
        if c['city'] in acceptable_centers:
            for day in c['availableDays']:
                d = {
                    "centerId": c['centerId'],
                    "day": day
                }
                r = client.post("https://frontdoornodepro.azurefd.net/sf/slots", json=d)
                print(r.json())

                if c['city'] == 'Barcelona':
                    print(c)
                    slots = r.json()
                    print(slots)
                    if 'error' in slots:
                        continue
                    last_slot = slots[-1]
                    d = {
                        "id": last_slot['id']
                    }
                    r = client.post("https://frontdoornodepro.azurefd.net/sf/schedule", json=d)
                    print(r)


def get_messages(webhook_token):
    url = f"https://webhook.site/token/{webhook_token}/requests?page=1&password=&sorting=newest"
    r = requests.get(url)
    d = r.json()['data']
    return d


def delete_message(webhook_token, message_id):
    url = f"https://webhook.site/token/{webhook_token}/request/{message_id}?password="
    r = requests.delete(url)


def get_code(webhook_token):
    time.sleep(2)
    i = 0
    while i < 20:
        print(f"Iter {i}")
        messages = get_messages(webhook_token)
        if not messages:
            i += 1
            time.sleep(5)
            continue

        content = messages[0].get('content')
        content = json.loads(content)
        code = parse_sms(content.get('message'))
        print("Code: {}".format(code))
        if code:
            delete_message(webhook_url, messages[0].get('uuid'))
            return code

        print(content)
        exit(1)

    return None


def parse_sms(sms_text):
    print(sms_text)
    # return re.search("La seva clau d\'accés (.*)", sms_text).group(1)
    return re.search("La seva clau d\'accés (.*) \(", sms_text).group(1)


if __name__ == '__main__':
    config = ConfigParser()
    script_folder = os.path.dirname(os.path.realpath(__file__))
    config.read(script_folder + '/.env')

    webhook_token = config.get("webhook", 'token')
    personal_data = {
        "documentID": config.get("personal_data", 'documentID'),
        "phone": config.get("personal_data", 'phone'),
        "name": config.get("personal_data", 'name'),
        "surname": config.get("personal_data", 'surname'),
        "surname2": config.get("personal_data", 'surname2'),
        "mail": config.get("personal_data", 'mail')
    }
    acceptable_centers = ['Barcelona']
    doit(personal_data, webhook_token)
