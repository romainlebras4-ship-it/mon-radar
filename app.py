import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import numpy as np

st.set_page_config(page_title="Terminal Alpha - Screener Institutionnel", layout="wide")

# ==============================================================================
# FONCTIONS TECHNIQUES (TRADUCTEUR & CALCUL RSI)
# ==============================================================================
def trouver_symbole(recherche):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={recherche}"
    try:
        reponse = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        donnees = reponse.json()
        if 'quotes' in donnees and len(donnees['quotes']) > 0:
            return donnees['quotes'][0]['symbol']
    except:
        pass
    return recherche

def calculer_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ==============================================================================
# INTERFACE & RÉGLAGES (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("🦅 Terminal Alpha")
    st.markdown("**Filtre d'Accumulation & Valorisation**")
    user_input = st.text_input("Entreprise ou Ticker :", "MSFT")
    annees = st.slider("Horizon d'analyse (Années)", 1, 10, 2)
    st.markdown("---")
    st.markdown("### ⚙️ Paramètres stricts")
    max_pe = st.number_input("Plafond P/E toléré", value=20)
    max_pb = st.number_input("Plafond P/B toléré", value=3.5)

# ==============================================================================
# MOTEUR D'ANALYSE
# ==============================================================================
if user_input:
    with st.spinner("Aspiration des bases de données et calcul des matrices..."):
        try:
            ticker = trouver_symbole(user_input).upper()
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period=f"{annees}y")
            
            if hist.empty:
                st.error("Données historiques introuvables.")
                st.stop()

            # --- CALCULS TECHNIQUES ---
            hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
            hist['SMA_200'] = hist['Close'].rolling(window=200).mean()
            hist['RSI'] = calculer_rsi(hist['Close'])
            rolling_max = hist['Close'].cummax()
            hist['Drawdown'] = ((hist['Close'] - rolling_max) / rolling_max) * 100
            
            prix_actuel = hist['Close'].iloc[-1]
            chute_actuelle = hist['Drawdown'].iloc[-1]
            rsi_actuel = hist['RSI'].iloc[-1] if not pd.isna(hist['RSI'].iloc[-1]) else 50

            # --- CALCULS FONDAMENTAUX (VALORISATION) ---
            pe_trailing = info.get('trailingPE', 0)
            pe_forward = info.get('forwardPE', 0)
            pb_ratio = info.get('priceToBook', 0)
            ps_ratio = info.get('priceToSalesTrailing12Months', 0)
            ev_ebitda = info.get('enterpriseToEbitda', 0)
            
            # --- CALCULS FONDAMENTAUX (SANTÉ FINANCIÈRE) ---
            debt_eq = info.get('debtToEquity', 0)
            current_ratio = info.get('currentRatio', 0)
            roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
            margins = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
            div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0

            # ==================================================================
            # EN-TÊTE : VERDICT D'ACCUMULATION
            # ==================================================================
            st.title(f"{info.get('longName', ticker)} ({ticker})")
            
            # Score d'accumulation basé sur la décote et la purge du marché
            score = 0
            if chute_actuelle < -20: score += 1
            if rsi_actuel < 40: score += 1
            if 0 < pe_trailing < max_pe: score += 1
            if 0 < pb_ratio < max_pb: score += 1
            if roe > 15: score += 1

            col_score, col_kpi1, col_kpi2, col_kpi3 = st.columns([2, 1, 1, 1])
            
            with col_score:
                if score >= 4:
                    st.success(f"**🎯 STATUT : OPPORTUNITÉ MAJEURE (Score {score}/5)**\n\nPessimisme extrême détecté couplé à une valorisation saine. Idéal pour une accumulation structurelle.")
                elif pe_trailing > max_pe or pb_ratio > (max_pb * 1.5):
                    st.error(f"**🔴 STATUT : REJETÉ (Surévaluation)**\n\nMultiples de valorisation trop élevés. Risque de destruction de capital. À exclure du portefeuille.")
                else:
                    st.warning(f"**⏳ STATUT : SOUS OBSERVATION (Score {score}/5)**\n\nAttendre une purge plus violente du marché ou une amélioration des fondamentaux.")

            with col_kpi1:
                st.metric("Prix Actuel", f"${prix_actuel:.2f}", f"{chute_actuelle:.2f}% depuis sommet", delta_color="inverse")
            with col_kpi2:
                st.metric("P/E Ratio", f"{pe_trailing:.1f}", "Sous-évalué" if 0 < pe_trailing < max_pe else "Surévalué", delta_color="inverse" if pe_trailing > max_pe else "normal")
            with col_kpi3:
                st.metric("Indice de Panique (RSI)", f"{rsi_actuel:.0f}/100", "Survendu (Pessimisme)" if rsi_actuel < 30 else "Neutre", delta_color="inverse" if rsi_actuel < 30 else "normal")

            st.markdown("---")

            # ==================================================================
            # ONGLET 1 : LA MATRICE DE VALORISATION MULTIPLE
            # ==================================================================
            st.subheader("⚖️ Scanner de Valorisation (Filtre anti-surévaluation)")
            v1, v2, v3, v4, v5 = st.columns(5)
            
            v1.metric("P/E (Passé)", f"{pe_trailing:.1f}", "< 20 idéal")
            v2.metric("P/E (Futur estimé)", f"{pe_forward:.1f}")
            v3.metric("Price / Book", f"{pb_ratio:.2f}", "< 3 idéal")
            v4.metric("Price / Sales", f"{ps_ratio:.2f}")
            v5.metric("EV / EBITDA", f"{ev_ebitda:.1f}", "< 15 idéal")

            st.markdown("---")

            # ==================================================================
            # ONGLET 2 : GRAPHIQUE PROFESSIONNEL (Prix, MMs, RSI, Volume)
            # ==================================================================
            st.subheader(f"📈 Radiographie Technique ({annees} ans)")
            
            # Création d'un graphique à 3 étages (Prix, Volume, RSI)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.05, 
                                row_heights=[0.6, 0.2, 0.2])

            # 1. Le Prix et les Moyennes Mobiles
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="Prix", line=dict(color="#00ff88")), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_50'], name="SMA 50", line=dict(color="#ffaa00", width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_200'], name="SMA 200", line=dict(color="#ff4b4b", width=1.5)), row=1, col=1)

            # 2. Les Volumes (Pour voir où les institutions capitulent)
            couleurs_volume = ['#ff4b4b' if row['Open'] > row['Close'] else '#00ff88' for index, row in hist.iterrows()]
            fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name="Volume", marker_color=couleurs_volume), row=2, col=1)

            # 3. Le RSI (Indicateur de Pessimisme Absolu)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name="RSI", line=dict(color="#00d4ff")), row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ff88", row=3, col=1, annotation_text="Pessimisme (Achat)")
            fig.add_hline(y=70, line_dash="dash", line_color="#ff4b4b", row=3, col=1, annotation_text="Euphorie (Vente)")

            fig.update_layout(template="plotly_dark", height=700, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # ==================================================================
            # ONGLET 3 : SANTÉ FINANCIÈRE (Le Filtre de Qualité)
            # ==================================================================
            st.markdown("---")
            st.subheader("🏦 Bilan & Qualité de l'Entreprise")
            
            q1, q2, q3, q4 = st.columns(4)
            with q1:
                st.info(f"**Rentabilité (ROE)**\n\n{roe:.1f}%" + (" ✅" if roe > 15 else " ❌"))
            with q2:
                st.info(f"**Marges Nettes**\n\n{margins:.1f}%" + (" ✅" if margins > 10 else " ❌"))
            with q3:
                st.info(f"**Dette / Capitaux**\n\n{debt_eq:.1f}%" + (" ✅" if debt_eq < 100 else " ❌"))
            with q4:
                st.info(f"**Rendement Dividende**\n\n{div_yield:.2f}%")

            # ==================================================================
            # GRAPHIQUE 4 : LA COURBE DE DRAWDOWN (Profondeur de crise)
            # ==================================================================
            st.subheader("🩸 Chronologie des purges (Drawdown)")
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(x=hist.index, y=hist['Drawdown'], fill='tozeroy', mode='lines', name='Chute %', line=dict(color='#ff4b4b')))
            fig_dd.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_dd, use_container_width=True)

        except Exception as e:
            st.error(f"Erreur système. Action non trouvée ou données inaccessibles. ({e})")
