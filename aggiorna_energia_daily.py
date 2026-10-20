import urllib.request
import json
from datetime import datetime
import os
import re
from bs4 import BeautifulSoup

NOME_FILE_JSON = "dati_energia_daily.json"

def scarica_da_energyindex():
    pun_trovato = None
    psv_trovato = None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    url_bersaglio = "https://www.energyindex.it/"

    try:
        req = urllib.request.Request(url_bersaglio, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # --- PUN ---
            elem_kwh = soup.find(string=re.compile('€/kWh', re.IGNORECASE))
            if elem_kwh:
                parent = elem_kwh.find_parent(['div', 'section', 'article', 'p', 'span'])
                text_block = parent.get_text() if parent else elem_kwh
                match = re.search(r'([0-1][,\.]\d{4})', text_block)
                if match:
                    pun_trovato = round(float(match.group(1).replace(',', '.')), 5)

            # --- PSV ---
            elem_smc = soup.find(string=re.compile('€/Smc', re.IGNORECASE))
            if elem_smc:
                parent = elem_smc.find_parent(['div', 'section', 'article', 'p', 'span'])
                text_block = parent.get_text() if parent else elem_smc
                match = re.search(r'([0-2][,\.]\d{4})', text_block)
                if match:
                    psv_trovato = round(float(match.group(1).replace(',', '.')), 5)

    except Exception as e:
        print(f"Avviso durante lo scraping: {e}")

    if not pun_trovato: pun_trovato = 0.2384  
    if not psv_trovato: psv_trovato = 0.8509  

    return pun_trovato, psv_trovato

def aggiorna_dati_json():
    oggi = datetime.now()
    oggi_str = oggi.strftime("%d/%m/%Y %H:%M")
    chiave_mese = oggi.strftime("%Y-%m") # E es: "2026-09"
    giorno_corrente = oggi.strftime("%d")
    
    pun_nuovo, psv_nuovo = scarica_da_energyindex()

    data = {"ultimo_aggiornamento": oggi_str, "storico_mesi": {}}
    if os.path.exists(NOME_FILE_JSON):
        try:
            with open(NOME_FILE_JSON, 'r', encoding='utf-8') as f:
                contenuto = json.load(f)
                if "storico_mesi" in contenuto:
                    data["storico_mesi"] = contenuto["storico_mesi"]
                elif "mese_corrente" in contenuto:
                    # Retrocompatibilità se c'era il vecchio formato
                    data["storico_mesi"][chiave_mese] = contenuto["mese_corrente"]
        except Exception as e:
            print(f"Errore lettura JSON: {e}")

    if chiave_mese not in data["storico_mesi"]:
        data["storico_mesi"][chiave_mese] = {
            "giorni": [],
            "pun_giornaliero": [],
            "psv_giornaliero": []
        }

    mese = data["storico_mesi"][chiave_mese]
    if giorno_corrente in mese["giorni"]:
        indice = mese["giorni"].index(giorno_corrente)
        mese["pun_giornaliero"][indice] = pun_nuovo
        mese["psv_giornaliero"][indice] = psv_nuovo
    else:
        mese["giorni"].append(giorno_corrente)
        mese["pun_giornaliero"].append(pun_nuovo)
        mese["psv_giornaliero"].append(psv_nuovo)

    # Calcolo medie
    if len(mese["pun_giornaliero"]) > 0:
        mese["media_pun_attuale"] = round(sum(mese["pun_giornaliero"]) / len(mese["pun_giornaliero"]), 5)
        mese["media_psv_attuale"] = round(sum(mese["psv_giornaliero"]) / len(mese["psv_giornaliero"]), 5)

    data["ultimo_aggiornamento"] = oggi_str

    try:
        with open(NOME_FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("File JSON aggiornato con successo.")
    except Exception as e:
        print(f"Errore salvataggio JSON: {e}")

if __name__ == "__main__":
    aggiorna_dati_json()
