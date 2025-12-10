# yugioh_price_tracker.py
import requests
import sqlite3
import datetime
import time
import os

# ---------- CONFIG ----------
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
#DB_NAME = r"C:\Users\plane\Desktop\ygh_track.db"  # raw string per Windows
DB_NAME = r"/home/plane/ygh/ygh_track.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Tabella carte (informazioni statiche)
cursor.execute('''
CREATE TABLE IF NOT EXISTS cards (
    card_id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    archetype TEXT
)
''')

# Tabella set (nome set, rarità, anno di uscita, card_id)
cursor.execute('''
CREATE TABLE IF NOT EXISTS card_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER,
    set_name TEXT,
    set_rarity TEXT,
    set_year INTEGER,
    FOREIGN KEY(card_id) REFERENCES cards(card_id)
)
''')

# Tabella prezzi (storico giornaliero)
cursor.execute('''
CREATE TABLE IF NOT EXISTS card_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER,
    date TEXT,
    cardmarket REAL,
    tcgplayer REAL,
    ebay REAL,
    amazon REAL,
    coolstuffinc REAL,
    FOREIGN KEY(card_id) REFERENCES cards(card_id)
)
''')

# Tabella prezzi stimati per rarità
cursor.execute('''
CREATE TABLE IF NOT EXISTS card_prices_by_rarity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER,
    set_name TEXT,
    set_rarity TEXT,
    price_estimated REAL,
    date TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(card_id)
)
''')

conn.commit()

# ---------- MOLTIPLICATORI PER RARITÀ ----------
rarity_multiplier = {
    "Common": 1.0,
    "Rare": 1.1,
    "Super Rare": 1.2,
    "Ultra Rare": 1.3,
    "Ultimate Rare": 1.5,
    "Secret Rare": 1.6,
    "Quarter Century Secret Rare": 1.7,
    "Platinum Secret Rare": 2.0,
    "Collector's Rare": 1.4
}

# ---------- FETCH DATA FROM API ----------
response = requests.get(API_URL)
data = response.json().get('data', [])

today = datetime.date.today().isoformat()

for card in data:
    card_id = card['id']
    name = card['name']
    type_ = card.get('type', '')
    archetype = card.get('archetype', '')

    # Inserisci o aggiorna la tabella cards
    cursor.execute('''
    INSERT OR IGNORE INTO cards (card_id, name, type, archetype)
    VALUES (?, ?, ?, ?)
    ''', (card_id, name, type_, archetype))

    # Inserisci card_sets
    for s in card.get('card_sets', []):
        set_name = s.get('set_name', '')
        set_rarity = s.get('set_rarity', '')
        set_date = s.get('set_date', '')  # es: "2021-05-01"
        
        # Estrai l'anno se disponibile
        if set_date:
            try:
                set_year = int(set_date.split('-')[0])
            except:
                set_year = None
        else:
            set_year = None

        cursor.execute('''
        INSERT OR IGNORE INTO card_sets (card_id, set_name, set_rarity, set_year)
        VALUES (?, ?, ?, ?)
        ''', (card_id, set_name, set_rarity, set_year))

    # Prezzi base
    prices = card.get('card_prices', [{}])[0]  # il primo elemento contiene i provider
    cardmarket = float(prices.get('cardmarket_price', 0))
    tcgplayer = float(prices.get('tcgplayer_price', 0))
    ebay = float(prices.get('ebay_price', 0))
    amazon = float(prices.get('amazon_price', 0))
    coolstuffinc = float(prices.get('coolstuffinc_price', 0))

    cursor.execute('''
    INSERT INTO card_prices (card_id, date, cardmarket, tcgplayer, ebay, amazon, coolstuffinc)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (card_id, today, cardmarket, tcgplayer, ebay, amazon, coolstuffinc))

    # Prezzi stimati per rarità
    for s in card.get('card_sets', []):
        rarity = s.get('set_rarity', 'Common')
        set_name = s.get('set_name', '')
        multiplier = rarity_multiplier.get(rarity, 1.0)
        price_estimated = round(cardmarket * multiplier, 2)
        cursor.execute('''
        INSERT INTO card_prices_by_rarity (card_id, set_name, set_rarity, price_estimated, date)
        VALUES (?, ?, ?, ?, ?)
        ''', (card_id, set_name, rarity, price_estimated, today))

    # Pausa opzionale per non sovraccaricare l'API
    # time.sleep(0.1)

conn.commit()
conn.close()

print(f"✅ Dati aggiornati per {len(data)} carte, snapshot del {today} salvato nel DB '{DB_NAME}'")
