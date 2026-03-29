import streamlit as st
import requests
import math
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="CornerAI Pro", page_icon="⚽", layout="centered")

# --- TWOJE STAŁE DANE ---
# Upewnij się, że Twój klucz API jest poprawny
API_KEY = "36e5f29c8dmshe7b8c927520f4a9p19f45djsnd0b026ad0d94"
HOST = "sofascore.p.rapidapi.com"
headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": HOST}

# --- FUNKCJE LOGICZNE (Zaktualizowane o linię) ---
def oblicz_prawdopodobienstwo(srednia_mecz, linia):
    # Poisson calculation for UNDER the line
    p_under = 0
    for k in range(int(linia) + 1):
        p_under += (srednia_mecz**k * math.exp(-srednia_mecz)) / math.factorial(k)
    
    # Calculate OVER probability
    szansa_over = (1 - p_under) * 100
    return szansa_over

def pobierz_pelne_staty(team_id, czy_gospodarz=True):
    url = f"https://{HOST}/teams/get-last-matches"
    params = {"teamId": team_id, "pageIndex": "0"}
    try:
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
    except:
        return 4.5, 4.5 # Default values on error

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("⚽ CornerAI Master")
st.markdown("Automatyczna analiza rzutów rożnych na podstawie statystyk PRO.")

with st.sidebar:
    st.header("💰 Twój Bankroll")
    budzet = st.number_input("Całkowity budżet (PLN)", value=1000)
    st.divider()
    st.header("⚙️ Ustawienia Analizy")
    
    # --- NOWY SUWAK WYBORU LINII ---
    wybrana_linia = st.select_slider(
        "Wybierz linię rzutów rożnych (Over)",
        options=[7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
        value=9.5
    )
    
    minimalna_szansa = st.slider("Minimalna szansa (%)", 50, 95, 65)

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
        try:
            res = requests.get(url, headers=headers, params={"date": today}).json()
            mecze = [m for m in res.get('events', []) if m.get('tournament', {}).get('id') == ligi[wybrana_liga]]
            
            if not mecze:
                st.warning("Brak meczów w tej lidze na dzisiaj.")
            else:
                st.info(f"Skanowanie dla linii: **Over {wybrana_linia}**")
                for mecz in mecze:
                    if mecz['status']['type'] != 'notstarted': continue
                    with st.spinner(f"Analizuję {mecz['homeTeam']['name']}..."):
                        h_a, h_o = pobierz_pelne_staty(mecz['homeTeam']['id'], True)
                        a_a, a_o = pobierz_pelne_staty(mecz['awayTeam']['id'], False)
                        suma = (h_a + a_a + h_o + a_o) / 2
                        
                        # Przekazujemy wybraną linię do funkcji
                        szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
                        
                        if szansa >= minimalna_szansa:
                            with st.expander(f"✅ {mecz['homeTeam']['name']} vs {mecz['awayTeam']['name']} - {szansa:.1f}%", expanded=True):
                                col1, col2, col3 = st.columns(3)
                                col1.metric("Średnia meczu", f"{suma:.2f}")
                                col2.metric("Kurs Sprawiedliwy", f"{100/szansa:.2f}")
                                col3.metric("Szansa (Over {wybrana_linia})", f"{szansa:.1f}%")
        except:
            st.error("Błąd połączenia z API. Spróbuj ponownie później.")

with tab2:
    st.subheader("Analiza konkretnego meczu (ID)")
    c1, c2 = st.columns(2)
    id_h = c1.text_input("ID Gospodarza")
    id_a = c2.text_input("ID Gościa")
    
    # Pokazujemy linię również w kalkulatorze ręcznym
    st.info(f"Analiza dla linii: **Over {wybrana_linia}** (ustawisz ją w pasku bocznym)")
    kurs_buka = st.number_input("Kurs u bukmachera (Over {wybrana_linia})", value=1.80)
    
    if st.button("ANALIZUJ MECZ"):
        if id_h and id_a:
            with st.spinner("Pobieram statystyki..."):
                h_a, h_o = pobierz_pelne_staty(id_h, True)
                a_a, a_o = pobierz_pelne_staty(id_a, False)
                suma = (h_a + a_a + h_o + a_o) / 2
                
                # Przekazujemy wybraną linię do funkcji
                szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
                
                st.info(f"Szansa na Over {wybrana_linia}: {szansa:.1f}% | Kurs sprawiedliwy: {100/szansa:.2f}")
                
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
                    st.error("Brak wartości (Value) w tym kursie.")
        else:
            st.warning("Wpisz oba ID drużyn.")
