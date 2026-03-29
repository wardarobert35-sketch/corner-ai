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
def oblicz_prawdopodobienstwo(srednia_mecz, linia):
    p_under = sum([(srednia_mecz**k * math.exp(-srednia_mecz)) / math.factorial(k) for k in range(int(linia) + 1)])
    return (1 - p_under) * 100

def pobierz_pelne_staty(team_id, czy_gospodarz=True):
    url = f"https://{HOST}/teams/get-last-matches"
    params = {"teamId": team_id, "pageIndex": "0"}
    res = requests.get(url, headers=headers, params=params).json()
    wybrane = []
    for m in res.get('events', []):
        id_domu = str(m['homeTeam']['id'])
        if (czy_gospodarz and id_domu == str(team_id)) or (not czy_gospodarz and id_domu != str(team_id)):
            wybrane.append(m)
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

# --- INTERFEJS ---
with st.sidebar:
    try:
        from PIL import Image
        st.image(Image.open('logo.jpg'), use_column_width=True)
    except: pass
    st.divider()
    st.header("💰 Bankroll")
    budzet = st.number_input("Budżet (PLN)", value=1000)
    st.divider()
    st.header("⚙️ Ustawienia")
    wybrana_linia = st.select_slider("Linia rzutów rożnych (Over)", options=[7.5, 8.5, 9.5, 10.5, 11.5], value=9.5)
    minimalna_szansa = st.slider("Min. szansa (%)", 50, 95, 65)

st.title("⚽ CornerAI Master Pro")
tab1, tab2 = st.tabs(["🌍 Globalny Skaner", "🧮 Kalkulator Ręczny"])

with tab1:
    ligi_dict = {"🌍 CAŁY ŚWIAT (Top Ligi)": 0, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": 39, "🇵🇱 Ekstraklasa": 106, "🇪🇸 La Liga": 140, "🇮🇹 Serie A": 135, "🇩🇪 Bundesliga": 78, "🇫🇷 Ligue 1": 137}
    wybor = st.selectbox("Zakres skanowania:", list(ligi_dict.keys()))
    
    if st.button("🚀 URUCHOM ANALIZĘ DZISIEJSZĄ"):
        today = datetime.now().strftime('%Y-%m-%d')
        res = requests.get(f"https://{HOST}/matches/list-by-date", headers=headers, params={"date": today}).json()
        wszystkie = res.get('events', [])
        
        if wybor == "🌍 CAŁY ŚWIAT (Top Ligi)":
            mecze = [m for m in wszystkie if m.get('tournament', {}).get('priority', 0) > 0]
        else:
            mecze = [m for m in wszystkie if m.get('tournament', {}).get('id') == ligi_dict[wybor]]
            
        if not mecze:
            st.warning("Brak meczów do analizy.")
        else:
            st.info(f"Analizuję {len(mecze)} spotkań dla linii Over {wybrana_linia}...")
            status = st.empty()
            okazje = 0
            for i, m in enumerate(mecze):
                if m['status']['type'] != 'notstarted': continue
                h_n, a_n = m['homeTeam']['name'], m['awayTeam']['name']
                status.text(f"⏳ ({i+1}/{len(mecze)}) Analizuję: {h_n} - {a_n}")
                try:
                    h_a, h_o = pobierz_pelne_staty(m['homeTeam']['id'], True)
                    a_a, a_o = pobierz_pelne_staty(m['awayTeam']['id'], False)
                    suma = (h_a + a_a + h_o + a_o) / 2
                    szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
                    if szansa >= minimalna_szansa:
                        okazje += 1
                        with st.expander(f"✅ {m['tournament']['name']}: {h_n} - {a_n} ({szansa:.1f}%)", expanded=True):
                            c1, c2, c3 = st.columns(3); c1.metric("Średnia", f"{suma:.2f}"); c2.metric("Kurs Fair", f"{100/szansa:.2f}"); c3.metric("Szansa", f"{szansa:.1f}%")
                except: continue
            status.success(f"Skanowanie zakończone! Znaleziono {okazje} okazji.")

with tab2:
    st.subheader("Manualny Kalkulator")
    c1, c2 = st.columns(2); id_h = c1.text_input("ID Gospodarza"); id_a = c2.text_input("ID Gościa")
    kurs_buka = st.number_input(f"Kurs u buka na Over {wybrana_linia}", value=1.80)
    if st.button("ANALIZUJ MECZ"):
        if id_h and id_a:
            with st.spinner("Pobieram dane..."):
                h_a, h_o = pobierz_pelne_staty(id_h, True); a_a, a_o = pobierz_pelne_staty(id_a, False)
                suma = (h_a + a_a + h_o + a_o) / 2; szansa = oblicz_prawdopodobienstwo(suma, wybrana_linia)
                st.info(f"Szansa: {szansa:.1f}% | Kurs fair: {100/szansa:.2f}")
                if kurs_buka > (100/szansa):
                    st.success("🔥 VALUEBET!"); p, b = szansa/100, kurs_buka-1
                    stawka = ((p*b - (1-p))/b) * 0.25 * budzet
                    st.write(f"Sugerowana stawka: **{max(0, stawka):.2f} PLN**")
                else: st.error("Brak wartości w tym kursie.")
