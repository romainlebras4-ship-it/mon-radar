# ==============================================================================
# 1. LES OUTILS (IMPORTS)
# ==============================================================================
import streamlit as st           # L'architecte qui crée la page web et l'interface
import yfinance as yf            # Le connecteur qui aspire les données de la Bourse
import plotly.graph_objects as go # Le dessinateur qui trace les graphiques interactifs
from datetime import datetime, timedelta # Pour calculer les dates (ex: il y a 2 ans)
import pandas as pd              # Le calculateur qui manipule les gros tableaux de chiffres
import requests                  # Pour envoyer des requêtes web (utilisé par le traducteur)

# ==============================================================================
# 2. CONFIGURATION DE L'INTERFACE
# ==============================================================================
# On règle la page en mode "large" (wide) pour avoir de la place pour les graphiques
st.set_page_config(page_title="Radar Pro - Value & Cycles", layout="wide")
st.title("🦅 Radar Pro : Stratégie d'Accumulation & Valorisation")

# ==============================================================================
# 3. LE TRADUCTEUR (NOM -> SYMBOLE BOURSIER)
# ==============================================================================
# Cette fonction secrète permet de taper "Microsoft" au lieu de chercher "MSFT"
def trouver_symbole(recherche):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={recherche}"
    headers = {'User-Agent': 'Mozilla/5.0'} # On se fait passer pour un navigateur classique
    try:
        reponse = requests.get(url, headers=headers)
        donnees = reponse.json()
        # Si Yahoo trouve une correspondance, on renvoie le symbole officiel
        if 'quotes' in donnees and len(donnees['quotes']) > 0:
            return donnees['quotes'][0]['symbol']
    except:
        pass
    return recherche # Si ça échoue, on garde ce que l'utilisateur a tapé

# ==============================================================================
# 4. LA BARRE DE RECHERCHE ET LES RÉGLAGES
# ==============================================================================
# On divise l'écran en deux colonnes (2/3 pour la recherche, 1/3 pour le curseur de temps)
col_search, col_time = st.columns([2, 1])

with col_search:
    user_input = st.text_input("Nom de l'entreprise ou Symbole :", "AAPL")

with col_time:
    # Un curseur allant de 1 à 10 ans pour ajuster la vision des cycles
    annees = st.slider("Période d'analyse des cycles (Années)", min_value=1, max_value=10, value=2)

# ==============================================================================
# 5. LE MOTEUR D'ANALYSE (Se lance quand on tape une recherche)
# ==============================================================================
if user_input:
    # Affiche une petite animation de chargement
    with st.spinner("Aspiration des bilans comptables et calcul des points de pessimisme..."):
        try:
            # 5A. Traduction et connexion à l'entreprise
            ticker_input = trouver_symbole(user_input).upper()
            st.write(f"🔍 **Entreprise analysée : {ticker_input}**")
            
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            # 5B. Récupération de l'historique des prix sur la période choisie
            hist = stock.history(period=f"{annees}y")
            if hist.empty:
                st.error("Aucune donnée historique trouvée pour cette période.")
                st.stop() # Arrête le programme si on ne trouve rien

            # 5C. Extraction des données financières complexes (Bilans, Cash Flow)
            cf = stock.cashflow
            fin = stock.financials

            # 5D. Mémorisation des indicateurs clés actuels
            current_price = info.get('currentPrice', hist['Close'].iloc[-1])
            high_period = hist['Close'].max()     # Le prix le plus haut de la période
            pe_ratio_actuel = info.get('trailingPE', 0) # Le ratio Cours/Bénéfice (Valorisation)
            
            # ==================================================================
            # 6. LE CALCUL DU PESSIMISME (DRAWDOWN)
            # ==================================================================
            # L'algorithme cherche le point le plus haut atteint, puis calcule 
            # mathématiquement le pourcentage de chute depuis ce sommet.
            rolling_max = hist['Close'].cummax()
            drawdown = ((hist['Close'] - rolling_max) / rolling_max) * 100
            chute_actuelle = drawdown.iloc[-1]
            
            st.markdown("---")
            
            # ==================================================================
            # 7. LE VERDICT DE LA STRATÉGIE
            # ==================================================================
            st.header("🤖 Signal Stratégique : Création d'ETF Personnel")
            c1, c2 = st.columns(2)
            
            with c1:
                # RÈGLE 1 : Si ça a chuté fort ET que c'est sous-évalué = ACHAT
                if chute_actuelle < -25 and 0 < pe_ratio_actuel < 18:
                    st.success("🟢 **ACHAT FORT : PESSIMISME EXTRÊME**\n\nValorisation basse et forte chute. Excellente fenêtre pour accumuler des positions et construire ton portefeuille.")
                
                # RÈGLE 2 : Bouclier anti-surévaluation. Si c'est trop cher = REJET DIRECT
                elif pe_ratio_actuel > 25:
                    st.error("🔴 **REJET : SURÉVALUATION**\n\nL'entreprise est trop chère. Valeur surévaluée typique des ETF classiques. À écarter de la sélection.")
                
                # RÈGLE 3 : Entre les deux = ATTENTE
                else:
                    st.warning("🟠 **NEUTRE**\n\nAttendre un point de pessimisme plus profond pour frapper au plus bas, ou une meilleure valorisation.")
            
            with c2:
                # Affichage des jauges à droite
                st.metric("Chute depuis le sommet", f"{chute_actuelle:.1f}%", delta_color="inverse")
                st.metric("Ratio P/E Actuel", f"{pe_ratio_actuel:.1f}")

            st.markdown("---")
            
            # ==================================================================
            # 8. LA CONSTRUCTION DES GRAPHIQUES (LES ONGLETS)
            # ==================================================================
            tab1, tab2, tab3 = st.tabs(["📉 Prix & Cycles", "🩸 Courbe de Pessimisme", "💰 Bilans Historiques (FCF & P/E)"])
            
            # ONGLET 1 : LE PRIX CLASSIQUE
            with tab1:
                fig_price = go.Figure()
                # On trace la ligne verte du prix
                fig_price.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Prix', line=dict(color='#00ff88')))
                # On trace la ligne rouge pointillée du sommet
                fig_price.add_hline(y=high_period, line_dash="dash", line_color="red", annotation_text=f"Sommet {annees} ans")
                fig_price.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_price, use_container_width=True)
                
            # ONGLET 2 : LA COURBE DE CHUTE (DRAWDOWN)
            with tab2:
                fig_dd = go.Figure()
                # On trace une zone rouge qui descend vers le bas pour montrer la profondeur de la crise
                fig_dd.add_trace(go.Scatter(x=drawdown.index, y=drawdown, fill='tozeroy', mode='lines', name='Chute %', line=dict(color='#ff4b4b')))
                fig_dd.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0), title="Recherche des points bas de marché")
                st.plotly_chart(fig_dd, use_container_width=True)

            # ONGLET 3 : LA RÉALITÉ COMPTABLE (LES BILANS)
            with tab3:
                st.markdown("### Évolution Comptable (Données officielles SEC / Yahoo)")
                col_fcf, col_pe = st.columns(2)
                
                # GRAPH 3A : LE FREE CASH FLOW (L'argent réel généré)
                with col_fcf:
                    if not cf.empty and 'Free Cash Flow' in cf.index:
                        # On récupère la ligne du FCF et on nettoie les trous
                        fcf_data = cf.loc['Free Cash Flow'].dropna().sort_index()
                        fig_fcf = go.Figure()
                        # Vert si l'entreprise gagne du cash, Rouge si elle en brûle
                        couleurs = ['#00ff88' if val > 0 else '#ff4b4b' for val in fcf_data.values]
                        fig_fcf.add_trace(go.Bar(x=fcf_data.index.year, y=fcf_data.values, marker_color=couleurs))
                        fig_fcf.update_layout(template="plotly_dark", title="Free Cash Flow Annuel", height=350, margin=dict(l=0, r=0, t=40, b=0))
                        st.plotly_chart(fig_fcf, use_container_width=True)
                    else:
                        st.warning("Historique du Free Cash Flow indisponible.")

                # GRAPH 3B : LE P/E HISTORIQUE (Pour vérifier si l'action devient de plus en plus chère)
                with col_pe:
                    if not fin.empty and 'Basic EPS' in fin.index:
                        eps_data = fin.loc['Basic EPS'].dropna().sort_index()
                        pe_dates, pe_values = [], []
                        
                        hist_pe = stock.history(period="5y") 
                        # On boucle sur chaque année où un bénéfice a été déclaré
                        for date, eps in eps_data.items():
                            if eps > 0: # L'entreprise doit être rentable pour calculer le P/E
                                try:
                                    # On cherche le prix de l'action à cette date précise dans le passé
                                    if date in hist_pe.index:
                                        prix_date = hist_pe.loc[date, 'Close']
                                    else:
                                        idx_proche = hist_pe.index.get_indexer([date], method='nearest')[0]
                                        prix_date = hist_pe.iloc[idx_proche]['Close']
                                    
                                    # Formule mathématique du P/E : Prix divisé par le Bénéfice (EPS)
                                    pe_values.append(prix_date / eps)
                                    pe_dates.append(date.year)
                                except:
                                    pass
                        
                        if pe_values:
                            fig_pe = go.Figure()
                            # On trace la courbe jaune du P/E
                            fig_pe.add_trace(go.Scatter(x=pe_dates, y=pe_values, mode='lines+markers', name='P/E Ratio', line=dict(color='#ffaa00', width=3), marker=dict(size=10)))
                            # On fixe la ligne rouge de danger : Le plafond de surévaluation
                            fig_pe.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Plafond Valeur (20x)")
                            fig_pe.update_layout(template="plotly_dark", title="Ratio P/E Historique (aux clôtures)", height=350, margin=dict(l=0, r=0, t=40, b=0))
                            st.plotly_chart(fig_pe, use_container_width=True)
                        else:
                            st.info("Bénéfices négatifs, P/E historique incalculable.")
                    else:
                        st.warning("Historique des bénéfices indisponible.")

        except Exception as e:
            # Sécurité finale si l'entreprise n'existe pas ou si Yahoo bloque la connexion
            st.error(f"Erreur de récupération. Les données de cette entreprise sont peut-être restreintes. ({e})")
