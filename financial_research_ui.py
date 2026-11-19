"""FHI company financial research UI | v2.4.0 | 2026-11-05.
Changelog: reconciled revenue-to-net-income Sankey, Buffett/Graham-inspired
research panels, explicit user-price valuation assumptions, no invented facts.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sec_financials import load_company, statements, overview, diagnostics, is_bank, bank_reconciliation
from value_research import assess, number
from market_reference import market_price, sec_common_shares


def _money(value):
    if value is None or pd.isna(value): return 'N/A'
    return f'${value/1e9:,.2f}B' if abs(value)>=1e9 else f'${value/1e6:,.1f}M'


def _percent(value):
    return 'N/A' if value is None else f'{value*100:,.1f}%'


def _sankey(income, bank=False):
    """Adaptive, period-aligned flow; never represent a negative Sankey edge."""
    if bank:
        st.caption('Banking presentation: cost of goods sold and gross profit are not conventional bank metrics.')
        # Reconciled net revenue to net income. This remains valid even when
        # the bank does not separately tag all credit-loss and noninterest costs.
        _bank_sankey(income)
        return
    if income.empty:
        st.info('No SEC income statement facts available for the selected frequency.')
        return
    # Select the newest period with revenue AND net income, not independent
    # latest non-null values from different fiscal periods.
    selected=None
    for period in income.columns:
        rev=income.at['Revenue',period] if 'Revenue' in income.index else None
        net=income.at['Net income',period] if 'Net income' in income.index else None
        if pd.notna(rev) and pd.notna(net) and rev>0:
            selected=period
            break
    if selected is None:
        st.info('No reporting period contains both revenue and net income. Review SEC data diagnostics below.')
        return
    def get(label):
        if label not in income.index:return None
        v=income.at[label,selected]
        return float(v) if pd.notna(v) else None
    revenue=get('Revenue'); cost=get('Cost of revenue')
    gross=get('Gross profit'); operating=get('Operating income'); net=get('Net income')
    if gross is None and cost is not None and 0<=cost<=revenue:
        gross=revenue-cost
    if cost is None and gross is not None and 0<=gross<=revenue:
        cost=revenue-gross
    if cost is None or gross is None or min(cost,gross)<0 or abs(revenue-cost-gross)>max(1e6,abs(revenue)*.01):
        # Honest minimal flow, useful even for sector-specific accounting.
        if net>=0 and net<=revenue:
            labels=['Revenue','Other costs and adjustments (residual)','Net income']
            vals=[revenue-net,net]
            src=[0,0]; dst=[1,2]
            colors=['#2F6FAD','#D36A70','#11A46B']
            caption='Simplified revenue-to-net-income view. Other costs and adjustments are a derived residual, NOT reported operating expenses.'
        else:
            st.info(f'Financial flow for {selected} cannot be reconciled safely; revenue and net income are available in the income statement.')
            return
    elif operating is not None and 0<=operating<=gross and 0<=net<=operating:
        opex=gross-operating; bridge=operating-net
        labels=['Revenue','Cost of revenue','Gross profit','Operating expenses (residual)',
                'Operating income','Other items and taxes (residual)','Net income']
        vals=[cost,gross,opex,operating,bridge,net]
        src=[0,0,2,2,4,4];dst=[1,2,3,4,5,6]
        colors=['#2F6FAD','#D36A70','#24956A','#D36A70','#24956A','#D36A70','#11A46B']
        caption='Operating expenses and other items/taxes are derived residuals, not separately reported SEC concepts.'
    elif net>=0 and net<=revenue:
        labels=['Revenue','Cost of revenue','Gross profit','Other costs and adjustments (residual)','Net income']
        vals=[cost,gross,gross-net,net]
        if gross<net:
            labels=['Revenue','Other costs and adjustments (residual)','Net income']
            vals=[revenue-net,net];src=[0,0];dst=[1,2]
            colors=['#2F6FAD','#D36A70','#11A46B']
        else:
            src=[0,0,2,2];dst=[1,2,3,4]
            colors=['#2F6FAD','#D36A70','#24956A','#D36A70','#11A46B']
        caption='Partial flow: operating income is missing or cannot be bridged. Residuals include all unshown costs, gains, and taxes.'
    else:
        st.info(f'Net loss or unusual accounting for {selected}; the income statement remains available. No misleading positive-only Sankey generated.')
        return
    if any(v<0 for v in vals):
        st.info('A valid nonnegative financial flow is unavailable for this reporting period.')
        return
    node_values=[revenue]+[0]*(len(labels)-1)
    for j,v in zip(dst,vals):node_values[j]+=v
    fig=go.Figure(go.Sankey(arrangement='snap',
        node=dict(pad=25,thickness=17,label=[f'{label}<br>{_money(node_values[i])}' for i,label in enumerate(labels)],color=colors),
        link=dict(source=src,target=dst,value=vals,
                  color=['rgba(50,110,165,.28)']*len(vals),
                  hovertemplate='%{source.label} → %{target.label}<br>%{value:$,.0f}<extra></extra>')))
    fig.update_layout(title=f'Revenue to net income · period ended {selected}',font=dict(color='#17263C',size=12),
                      paper_bgcolor='white',height=420,margin=dict(l=15,r=15,t=55,b=15))
    st.plotly_chart(fig,use_container_width=True)
    st.caption(caption)


def _bank_sankey(income):
    """Draw bank-specific flows only where same-period numbers reconcile."""
    period=next((p for p in income.columns if 'Revenue' in income.index
                 and 'Net income' in income.index and pd.notna(income.at['Revenue',p])
                 and pd.notna(income.at['Net income',p])
                 and 0 <= income.at['Net income',p] <= income.at['Revenue',p]),None)
    if period is None:
        st.info('No same-period bank net revenue and net income can be reconciled.')
        return
    def v(label):
        if label not in income.index: return None
        x=income.at[label,period]
        return float(x) if pd.notna(x) else None
    rev=v('Revenue');net=v('Net income');ii=v('Bank interest income');ie=v('Bank interest expense')
    nii=v('Net interest income');other=v('Noninterest income')
    provision=v('Provision for credit losses');opex=v('Noninterest expense')
    pretax=v('Income before tax');tax=v('Income tax expense')
    labels=[];colors=[];src=[];dst=[];values=[];link_colors=[]
    def node(label,amount,color):
        labels.append(f'{label}<br>{_money(amount)}');colors.append(color)
        return len(labels)-1
    def edge(a,b,amount,color):
        if amount is not None and amount>=0:
            src.append(a);dst.append(b);values.append(amount);link_colors.append(color)
    blue='#3277B5';green='#19966B';red='#CE626D'
    checks=bank_reconciliation(income,period)
    status=dict(zip(checks['Relationship'],checks['Status']))
    # Detailed interest flow is used only if both interest and net-revenue
    # relationships are validated and all component flows are nonnegative.
    detailed=(status.get('Net interest income')=='Reconciled' and
              status.get('Net revenue')=='Reconciled' and
              None not in (ii,ie,nii,other) and min(ii,ie,nii,other)>=0)
    if detailed:
        interest=node('Interest income',ii,blue)
        funding=node('Interest expense',ie,red)
        netinterest=node('Net interest income',nii,green)
        othernode=node('Noninterest income',other,blue)
        revenue=node('Net revenue',rev,blue)
        edge(interest,funding,ie,'rgba(206,98,109,.28)')
        edge(interest,netinterest,nii,'rgba(25,150,107,.28)')
        edge(netinterest,revenue,nii,'rgba(25,150,107,.28)')
        edge(othernode,revenue,other,'rgba(50,119,181,.28)')
    else:
        revenue=node('Net revenue',rev,blue)
    # Detailed expenses only if they reconcile to pretax income.
    detailed_exp=(status.get('Pretax income')=='Reconciled' and
                  None not in (provision,opex,pretax) and
                  min(provision,opex,pretax)>=0)
    if detailed_exp:
        credit=node('Credit-loss provision',provision,red)
        expenses=node('Noninterest expense',opex,red)
        beforetax=node('Income before tax',pretax,green)
        edge(revenue,credit,provision,'rgba(206,98,109,.28)')
        edge(revenue,expenses,opex,'rgba(206,98,109,.28)')
        edge(revenue,beforetax,pretax,'rgba(25,150,107,.28)')
        remaining=beforetax
    else:
        remaining=revenue
    # A reported tax bridge is used only when its figures reconcile.
    tax_bridge=(status.get('Net income')=='Reconciled' and tax is not None
                and tax>=0 and (detailed_exp or abs(rev-pretax)<max(1e6,rev*.015) if pretax is not None else False))
    if tax_bridge:
        taxnode=node('Income taxes',tax,red)
        netnode=node('Net income',net,green)
        edge(remaining,taxnode,tax,'rgba(206,98,109,.28)')
        edge(remaining,netnode,net,'rgba(25,150,107,.28)')
    else:
        base=pretax if detailed_exp else rev
        residual=base-net
        if residual < 0:
            st.info('Unusual gains or losses prevent a nonnegative financial Sankey. See income statement.')
            return
        residualnode=node('Other costs and adjustments (residual)',residual,red)
        netnode=node('Net income',net,green)
        edge(remaining,residualnode,residual,'rgba(206,98,109,.28)')
        edge(remaining,netnode,net,'rgba(25,150,107,.28)')
    fig=go.Figure(go.Sankey(arrangement='snap',
         node=dict(label=labels,pad=20,thickness=18,color=colors),
         link=dict(source=src,target=dst,value=values,color=link_colors,
                   hovertemplate='%{source.label} → %{target.label}<br>$%{value:,.0f}<extra></extra>')))
    fig.update_layout(title=f'Banking revenue and earnings · period ended {period}',
                      height=490,font=dict(color='#17263C',size=12),
                      paper_bgcolor='white',margin=dict(l=12,r=12,t=55,b=10))
    st.plotly_chart(fig,use_container_width=True)
    st.caption('Detailed flows require matching SEC facts and reconciliation. Residuals are calculated, not reported expense lines.')
    with st.expander('Bank financial reconciliation — automatic checks'):
        st.dataframe(checks.style.format({'Reported':'${:,.0f}','Calculated':'${:,.0f}','Difference':'${:,.0f}'},na_rep='—'),
                     use_container_width=True,hide_index=True)


def _statement(tab,name,stmts,ticker,cadence):
    with tab:
        df,provenance=stmts[name]
        if df.empty or df.isna().all().all():
            st.info('No comparable standardized SEC facts available for this statement and period.')
            return
        display=df.copy()
        for label in display.index:
            if label!='Diluted EPS': display.loc[label]=display.loc[label]/1e6
        st.caption('USD millions except diluted EPS (USD/share). A dash means unavailable, not zero. Derived figures are identified below.')
        st.dataframe(display.style.format('{:,.2f}',na_rep='—'),use_container_width=True)
        derived = [
            {'Metric': label, 'Period': period, 'Calculation': info[2]}
            for (label, period), info in provenance.items()
            if len(info) >= 3 and str(info[2]).startswith('derived:')
        ]
        if derived:
            with st.expander('Calculated figures — formula and reporting period'):
                st.dataframe(pd.DataFrame(derived), hide_index=True, use_container_width=True)
        st.download_button('Download CSV',df.to_csv(index_label='Metric').encode(),
                           file_name=f'{ticker}_{name.lower().replace(" ","_")}_{cadence.lower()}.csv',
                           mime='text/csv',key=f'sec_export_{name}')


def _checks(df):
    d=df.copy()
    d['Status']=d['Pass'].map({True:'Meets guideline',False:'Does not meet',None:'Insufficient data'})
    d['Observed']=d['Observed'].map(lambda v:f'{v:.3f}' if isinstance(v,float) else str(v) if v is not None else '—')
    st.dataframe(d[['Indicator','Observed','Status','Interpretation']],hide_index=True,use_container_width=True)


def render_financial_research(ticker):
    st.divider()
    st.header('Company financial research')
    st.caption('SEC filings · Buffett/Graham-inspired screening · source-based evidence, not investment advice.')
    with st.spinner(f'Loading SEC financial filings for {ticker}...'):
        try: data,cik,legal_name=load_company(ticker)
        except Exception as exc:
            st.warning(f'Financial statements unavailable for {ticker}: {exc}')
            return
    st.markdown(f'**{ticker} — {legal_name}** · SEC CIK {cik:010d}')
    st.link_button('SEC company filings ↗',f'https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude')
    cadence=st.radio('Reporting frequency',['Annual','Quarterly'],horizontal=True,key='sec_frequency')
    periods=st.slider('Periods to display',3,10,6,key='sec_periods')
    bank=is_bank(data,ticker)
    if bank: st.info('Bank-specific financial statement: interest income, funding costs, credit losses and noninterest expenses. Unreported values remain unavailable.')
    stmts=statements(data,'annual' if cadence=='Annual' else 'quarterly',periods,ticker=ticker)
    # Quality and Graham evidence always use annual records, regardless of statement view.
    annual=statements(data,'annual',10,ticker=ticker)
    assessment=assess(annual)
    if bank: st.warning('Buffett/Graham generic screening metrics may be unsuitable for banks. Interpret quality and valuation scores cautiously; bank-specific capital ratios are not yet implemented.')
    tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(['Financial overview','Income statement','Balance sheet','Cash flow','Business quality','Conservative value'])
    with tab1:
        metrics=overview(stmts)
        for labels in [('Revenue','Net income','Operating margin %','Net margin %'),
                       ('Total assets','Total liabilities','Operating cash flow','Free cash flow')]:
            cols=st.columns(4)
            for col,label in zip(cols,labels):
                v=metrics[label]
                col.metric(label,f'{v:.1f}%' if v is not None and label.endswith('%') else _money(v))
        income=stmts['Income Statement'][0]
        if not income.empty:
            _sankey(income,bank=bank)
            fig=go.Figure()
            for label in ['Revenue','Operating income','Net income']:
                if label in income.index and income.loc[label].notna().any():
                    values=(income.loc[label]/1e9).iloc[::-1]
                    fig.add_trace(go.Bar(
                        name=label,
                        x=list(income.columns)[::-1],
                        y=values,
                        text=[f'${v:,.2f}B' if pd.notna(v) else '' for v in values],
                        textposition='outside',
                        textfont=dict(size=11, color='#17263C'),
                        cliponaxis=False,
                        hovertemplate='%{x}<br>%{fullData.name}: $%{y:,.2f}B<extra></extra>',
                    ))
            fig.update_layout(title='Revenue and earnings history',barmode='group',template='plotly_white',
                              yaxis_title='USD billions',hoverlabel=dict(bgcolor='white',font_color='#17263C'),height=420,
                              margin=dict(t=80,b=50,l=55,r=25),uniformtext_minsize=9,uniformtext_mode='hide')
            st.plotly_chart(fig,use_container_width=True)
        st.info('SEC filings do not supply current stock prices or forward valuation multiples. Business-segment revenue is shown only when reliably sourced.')
    _statement(tab2,'Income Statement',stmts,ticker,cadence)
    _statement(tab3,'Balance Sheet',stmts,ticker,cadence)
    _statement(tab4,'Cash Flow',stmts,ticker,cadence)
    with tab5:
        st.subheader('Buffett-inspired business quality')
        st.caption('Original, transparent heuristic checks. Not Warren Buffett’s proprietary model. Qualitative moat and management assessment still required.')
        c1,c2,c3=st.columns(3)
        c1.metric('Quality evidence score',f"{assessment['quality_score']}/100" if assessment['quality_score'] is not None else 'Not rated')
        c2.metric('Return on equity',_percent(assessment['roe']))
        c3.metric('Operating margin',_percent(assessment['operating_margin']))
        _checks(assessment['quality_checks'])
        st.caption('Equal-weight checks are research indicators, not predictions. Four available checks are required for a score; missing checks are excluded and visible.')
        st.markdown('**Qualitative due diligence:** competitive moat · understandable business model · management capital allocation · earnings predictability.')
    with tab6:
        st.subheader('Graham-inspired conservative value')
        st.caption('Financial conservatism is evaluated separately from market valuation. Classic thresholds are unsuitable for some sectors, especially financials.')
        c1,c2,c3=st.columns(3)
        c1.metric('Financial conservatism',f"{assessment['graham_evidence_score']}/100" if assessment['graham_evidence_score'] is not None else 'Not rated')
        c2.metric('Current ratio',f"{assessment['current_ratio']:.2f}" if assessment['current_ratio'] is not None else 'N/A')
        c3.metric('Liabilities / assets',_percent(assessment['liabilities_assets']))
        _checks(assessment['graham_checks'])
        st.markdown('**Graham Number reference — automatically populated**')
        st.caption('Latest available market close and SEC-reported common shares outstanding. Dates may differ; this is a screening reference, not a verified intrinsic value.')
        shares_ref=sec_common_shares(data)
        try:
            price_ref=market_price(ticker)
        except Exception as exc:
            price_ref=None
            st.warning(f'Automatic price lookup unavailable: {exc}')
        if shares_ref:
            st.caption(f"Shares: {shares_ref['shares']/1e6:,.2f} million · as of {shares_ref['as_of']} · filed {shares_ref['filed']} · {shares_ref['source']}")
        else:
            st.warning('No current common shares outstanding fact found in SEC Company Facts.')
        if price_ref:
            st.caption(f"Share price: ${price_ref['price']:,.2f} · close {price_ref['as_of']} · {price_ref['source']}")
        else:
            st.warning('No share price available from the market-data source.')
        if price_ref and shares_ref and price_ref['currency']=='USD':
            val=assess(annual,price=price_ref['price'],shares=shares_ref['shares'])
            v1,v2,v3=st.columns(3)
            v1.metric('Book value / share',f"${val['bvps']:,.2f}" if val['bvps'] is not None else 'N/A')
            v2.metric('Graham Number',f"${val['graham_number']:,.2f}" if val['graham_number'] is not None else 'Not applicable')
            v3.metric('Discount to Graham Number',_percent(val['margin_of_safety']))
            st.caption('Uses positive diluted EPS and book equity from SEC filings; SEC common shares outstanding may be from a different date. Verify share class, split adjustments and reporting dates. The discount is not a verified margin of safety.')
        else:
            st.info('Graham valuation is withheld until both an eligible USD share price and SEC common-share count are available.')
    with st.expander('Financial completeness and derivation notes'):
        st.write('Operating income is shown only when explicitly reported using a supported SEC concept. It is not inferred from net income, because that would misclassify taxes and non-operating items.')
        st.write('Total liabilities may be derived as total assets minus stockholders equity for the same balance-sheet date; the source is labeled derived in the statement provenance.')
        st.write('If a company does not publish an operating income subtotal, the Sankey uses a labeled residual rather than an invented operating income figure.')
    with st.expander('SEC financial data diagnostics — concepts, periods and missing values'):
        st.dataframe(diagnostics(data,'annual' if cadence=='Annual' else 'quarterly',periods),hide_index=True,use_container_width=True)
    st.caption('Source: SEC EDGAR XBRL companyfacts. Verify figures, reporting periods and amendments against issuer filings. Scores are original research heuristics.')
