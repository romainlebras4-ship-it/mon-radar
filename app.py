import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="Radar Pro - Value & Cycles", layout="wide")
st.title("🦅 Radar Pro : Fondamentaux & Cycles d'Accumulation")

# --- LE TRADUCTEUR NOM -> SYMBOLE ---
def trouver_symbole(recherche):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={recherche}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        reponse = requests.get(url, headers=headers)
        donnees = reponse.json()
        if 'quotes' in donnees and len(donnees['quotes']) > 0:
            return donnees['quotes'][0]['symbol']
    except:
        pass
    return recherche

# La barre de recherche accepte maintenant les noms complets
user_input = st.text_input("Nom de l'entreprise ou Symbole (ex: ServiceNow, Total, AAPL) :", "AAPL")

if user_input:
    with st.spinner("Recherche de l'entreprise et analyse des bilans en cours..."):
        try:
            # Traduction automatique
            ticker_input = trouver_symbole(user_input).upper()
            st.write(f"🔍 **Entreprise identifiée : {ticker_input}**")
            
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            # Historique sur 2 ans pour identifier les creux de marché
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            hist = stock.history(start=start_date, end=end_date)
            
            current_price = info.get('currentPrice', hist['Close'].iloc[-1] if not hist.empty else 0)
            high_2y = hist['Close'].max() if not hist.empty else current_price
            pe_ratio = info.get('trailingPE', 0)
            fcf = info.get('freeCashflow', 0)
            debt_eq = info.get('debtToEquity', 0)
            margins = info.get('profitMargins', 0) * 100
            
            chute = ((high_2y - current_price) / high_2y) * 100 if high_2y > 0 else 0
            
            st.markdown("---")
            st.header("🤖 Signal Stratégique (Pessimisme & Valorisation)")
            
            c1, c2 = st.columns(2)
            with c1:
                if chute > 25 and 0 < pe_ratio < 18:
                    st.success("🟢 **ACHAT FORT : PESSIMISME MAXIMUM**\n\nL'action est massacrée mais la valorisation est excellente. Fenêtre d'accumulation ouverte.")
                elif pe_ratio > 25:
                    st.error("🔴 **REJET : SURÉVALUATION**\n\nEntreprise trop chère. Typique des valeurs qui gonflent artificiellement les ETF. À fuir.")
                else:
                    st.warning("🟠 **NEUTRE : ATTENTE**\n\nPas de panique extrême ou valorisation moyenne. Patienter pour le prochain cycle bas.")
                    
            with c2:
                st.metric("Ratio P/E (Cible < 20)", f"{pe_ratio:.1f}")
                st.metric("Chute depuis le sommet (2 ans)", f"-{chute:.1f}%")

            st.markdown("---")
            st.header("📊 Filtres de Qualité (Type Graham)")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"✅ Marges Nettes : {margins:.1f}%" if margins > 10 else f"❌ Marges faibles : {margins:.1f}%")
            with col2:
                st.info("✅ Dette Maîtrisée" if debt_eq < 100 else "❌ Dette Élevée")
            with col3:
                st.info("✅ Génère du Cash (FCF Positif)" if fcf > 0 else "❌ Brûle du Cash (FCF Négatif)")

            st.markdown("---")
            st.header("📉 Évolution des Prix (Cycle 24 mois)")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color='#00ff88')))
            fig.add_hline(y=high_2y, line_dash="dash", line_color="red", annotation_text="Sommet 2 ans")
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error("Erreur de récupération. L'entreprise n'a pas été trouvée ou les données sont indisponibles.")

        except Exception as e:
            st.error("Erreur de récupération. Vérifiez le symbole de l'action.")
