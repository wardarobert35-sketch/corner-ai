import streamlit as st
import requests
import math
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="CornerAI Pro", page_icon="⚽", layout="centered")

# --- TWOJE STAŁE DANE ---
API_KEY = "36e5f29c8dmshe7b8c927520f4a9p19f45djsnd0b026ad0d94"
HOST = "sofascore.p.rapidapi.com"
headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": HOST}

# --- FUNKCJE LOGICZNE ---
def oblicz_prawdopodobienstwo(srednia_mecz, linia=9.5):
    p_under = sum([(srednia_mecz**k * math.exp(-srednia_mecz)) / math.factorial(k) for k in range(int(linia) + 1)])
    return (1 - p_under) * 100

def pobierz_pelne_staty(team_id, czy_gospodarz=True):
    url = f"https://{HOST}/teams/get-last-matches"
    params = {"teamId": team_id, "pageIndex": "0"}
    res = requests.get(url, headers=headers, params=params).json()
    wszystkie = res.get('events', [])
    wybrane = []
    for m in wszystkie:
        id_domu = str(m['homeTeam']['id'])
        if czy_gospodarz and id_domu == str(team_id): wybrane.append(m)
        elif not czy_gospodarz and id_domu != str(team_id): wybrane.append(m)
        if len(wybrane) == 5: break
    nabite, stracone, licznik = 0, 0, 0
    for m in wybrane:
        s_res = requests.get(f"https://{HOST}/matches/get-statistics", headers=headers, params={"matchId": m['id']}).json()
        try:
            for g in s_res['statistics'][0]['groups']:
                for i in g['statisticsItems']:
                    if i['name'] == 'Corner kicks':
                        if czy_gospodarz:
                            nabite += int(i['home']); stracone += int(i['away'])
                        else:
                            nabite += int(i['away']); stracone += int(i['home'])
                        licznik += 1
        except: continue
    return (nabite/licznik if licznik>0 else 4.5), (stracone/licznik if licznik>0 else 4.5)

# ==========================================
# --- 🖥️ INTERFEJS UŻYTKOWNIKA ---
# ==========================================

# Tytuł główny
st.title("⚽ CornerAI Master")
st.markdown("Automatyczna analiza rzutów rożnych na podstawie statystyk PRO.")

# --- PASEK BOCZNY (Sidebar) ---
with st.sidebar:
    
    # KROK 1: DODANIE LOGO NA GÓRZE PASKA BOCZNEGO
    try:
        # Wczytujemy logo z GitHuba (jeśli plik nazywa się logo.png)
        from PIL import Image
        image = Image.open('logo.jpg')
        st.image(image, use_column_width=True)
    except:
        # Jeśli pliku nie ma lub jest błąd, ignorujemy to (bezpiecznik)
        pass
    
    st.divider() # Estetyczna linia oddzielająca
    
    # KROK 2: DALSZE USTAWIENIA (Twoje stare pola)
    st.header("💰 Twój Bankroll")
    budzet = st.number_input("Całkowity budżet (PLN)", value=1000)
    st.divider()
    st.header("⚙️ Ustawienia Analizy")
    wybrana_linia = st.select_slider(
        "Wybierz linię rzutów rożnych (Over)",
        options=[7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
        value=9.5
    )
    minimalna_szansa = st.slider("Minimalna szansa (%)", 50, 95, 65)

# --- ZAKŁADKI GŁÓWNE ---
tab1, tab2 = st.tabs(["🚀 Skaner Lig", "🧮 Kalkulator Ręczny"])

with tab1:
    ligi = {
        "Anglia: Premier League": 39, "Polska: Ekstraklasa": 106,
        "Hiszpania: La Liga": 140, "Włochy: Serie A": 135,
        "Niemcy: Bundesliga": 78, "Francja: Ligue 1": 137
    }
    wybrana_liga = st.selectbox("Wybierz ligę:", list(ligi.keys()))
    
    if st.button("URUCHOM SKANOWANIE"):
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://{HOST}/matches/list-by-date"
        res = requests.get(url, headers=headers, params={"date": today}).json()
        mecze = [m for m in res.get('events', []) if m.get('tournament', {}).get('id') == ligi[wybrana_liga]]
        
        if not mecze:
            st.warning("Brak meczów w tej lidze na dzisiaj.")
        else:
            # Informujemy użytkownika, jaką linię skanujemy
            st.info(f"Skanowanie dla linii: **Over {wybrana_linia}**")
            for mecz in mecze:
                if mecz['status']['type'] != 'notstarted': continue
                with st.spinner(f"Analizuję {mecz['homeTeam']['name']}..."):
                    h_a, h_o = pobierz_pelne_staty(mecz['homeTeam']['id'], True)
                    a_a, a_o = pobierz_pelne_staty(mecz['awayTeam']['id'], False)
                    suma = (h_a + a_a + h_o + a_o) / 2
                    # Przekazujemy linię do funkcji
                    szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
                    
                    if szansa >= minimalna_szansa:
                        with st.expander(f"✅ {mecz['homeTeam']['name']} vs {mecz['awayTeam']['name']} - {szansa:.1f}%", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Średnia meczu", f"{suma:.2f}")
                            col2.metric("Kurs Sprawiedliwy", f"{100/szansa:.2f}")
                            # Pokazujemy linię w tytule
                            col3.metric(f"Szansa (Over {wybrana_linia})", f"{szansa:.1f}%")

with tab2:
    st.subheader("Analiza konkretnego meczu (ID)")
    c1, c2 = st.columns(2)
    id_h = c1.text_input("ID Gospodarza")
    id_a = c2.text_input("ID Gościa")
    
    # Informacja o linii również w kalkulatorze ręcznym
    st.info(f"Analiza dla linii: **Over {wybrana_linia}** (ustawisz ją w pasku bocznym)")
    kurs_buka = st.number_input(f"Kurs u bukmachera (Over {wybrana_linia})", value=1.80)
    
    if st.button("ANALIZUJ MECZ"):
        if id_h and id_a:
            h_a, h_o = pobierz_pelne_staty(id_h, True)
            a_a, a_o = pobierz_pelne_staty(id_a, False)
            suma = (h_a + a_a + h_o + a_o) / 2
            # Przekazujemy linię do funkcji
            szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
            
            st.info(f"Szansa na Over {wybrana_linia}: {szansa:.1f}% | Kurs sprawiedliwy: {100/szansa:.2f}")
            
            # Zapobiegamy dzieleniu przez zero
            kurs_b_fair = 100/szansa if szansa > 0 else 100
            
            if kurs_buka > kurs_b_fair:
                st.success("🔥 TO JEST VALUEBET!")
                # Kalkulator Kelly'ego
                p, b = szansa/100, kurs_buka-1
                if b > 0:
                    stawka_f = ((p*b - (1-p))/b)
                    # Stosujemy Fractional Kelly (1/4) dla bezpieczeństwa
                    stawka = stawka_f * 0.25 * budzet
                    st.write(f"Sugerowana stawka (Quarter-Kelly): **{max(0, stawka):.2f} PLN**")
                else:
                    st.write("Kurs bukmachera musi być wyższy niż 1.0")
            else:
                st.error("Brak wartości w tym kursie.")
        else:
            st.warning("Wpisz oba ID drużyn.")
