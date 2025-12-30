import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time

# --- ASETUKSET ---
SYMBOL = 'BTC/EUR'
exchange = ccxt.bitstamp({'enableRateLimit': True})

st.set_page_config(page_title="SENTINEL MASTER WEB", layout="centered")

st.title("🚀 SENTINEL MASTER v3.6 - Web Edition")
st.write(f"Reaaliaikainen seuranta: **{SYMBOL}**")

# Tyhjät paikat tiedoille, jotka päivittyvät
price_placeholder = st.empty()
prediction_placeholder = st.empty()
metrics_placeholder = st.empty()
activity_placeholder = st.empty()

def fetch_market_data():
    try:
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # Volyymi-analyysi
        avg_vol = df['vol'].iloc[:-1].mean()
        current_vol = df['vol'].iloc[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        # Indikaattorit
        volat = (df['high'] - df['low']).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain/(loss + 0.001)))).iloc[-1]
        
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd = (ema12 - ema26).iloc[-1]
        signal = (ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1]
        
        # Tilauskirja
        ob = exchange.fetch_order_book(SYMBOL, limit=20)
        bid_v = int(sum([x[1] for x in ob['bids']]))
        ask_v = int(sum([x[1] for x in ob['asks']]))
        
        return {
            'price': df['close'].iloc[-1], 'rsi': rsi, 'macd': macd, 'macd_s': signal, 
            'pressure': bid_v/(ask_v+0.01), 'volat': volat, 'bids': bid_v, 'asks': ask_v, 'vol_ratio': vol_ratio
        }
    except Exception as e:
        st.error(f"Virhe datan haussa: {e}")
        return None

# PÄÄSILMUKKA
while True:
    data = fetch_market_data()
    
    if data:
        # 1. Hinnan näyttö
        price_placeholder.metric(label="Bitcoin Hinta (EUR)", value=f"{data['price']:,.2f} €")

        # 2. Ennuste-logiikka
        move = data['volat'] * max(data['pressure'], 0.5)
        
        with prediction_placeholder.container():
            if (data['rsi'] < 45 and data['macd'] > data['macd_s']) or data['pressure'] > 2.2:
                st.success(f"### ENNUSTE: NOUSU 📈 \n Tavoite: {data['price']+move:,.2f} € (+{move:.2f} €)")
            elif (data['rsi'] > 55 and data['macd'] < data['macd_s']) or data['pressure'] < 0.45:
                st.error(f"### ENNUSTE: LASKU 📉 \n Tavoite: {data['price']-move:,.2f} € (-{move:.2f} €)")
            else:
                st.info("### TILANNE: NEUTRAALI ⚖️ \n Odotetaan vahvistusta...")

        # 3. Mittarit sarakkeissa
        with metrics_placeholder.container():
            col1, col2, col3 = st.columns(3)
            
            rsi_color = "normal" if 40 <= data['rsi'] <= 60 else ("inverse" if data['rsi'] > 60 else "normal")
            col1.metric("RSI (Voima)", f"{data['rsi']:.1f}")
            
            trend = "YLÖS" if data['macd'] > data['macd_s'] else "ALAS"
            col2.metric("Trendi", trend)
            
            col3.metric("Heilahtelu", f"± {data['volat']:.2f} €")

        # 4. Aktiivisuus ja Paine
        with activity_placeholder.container():
            st.write("---")
            st.write(f"**Ostajat:** {data['bids']} | **Myyjät:** {data['asks']}")
            
            v_rat = data['vol_ratio']
            if v_rat > 2.5:
                st.warning(f"🔥 HUOMIO: Erittäin korkea aktiivisuus ({v_rat:.1f}x)!")
            elif v_rat > 1.2:
                st.write(f"✅ Markkinan aktiivisuus kasvussa ({v_rat:.1f}x)")
            
            st.caption("⏱ Arvio toteutuu yleensä 5–15 minuutin kuluessa.")

    time.sleep(10)
