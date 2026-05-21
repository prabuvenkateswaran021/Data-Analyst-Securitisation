"""
Build supplementary star-schema tables to extend the four uploaded source files
into a full enterprise securitisation model.

Produces:
  Dimensions:  dim_calendar, dim_borrower, dim_vehicle, dim_geography,
               dim_servicer, dim_pool, dim_tranche, dim_investor,
               dim_scenario, dim_economic_indicator
  Facts:       fact_loan (curated), fact_dpd_snapshot, fact_loss_monthly,
               fact_vintage, fact_tranche_cashflow, fact_waterfall_distribution,
               fact_stress_results, fact_economic_history
"""
import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)
SRC = Path('/mnt/user-data/uploads')
OUT = Path('/home/claude/build/01_data')
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# 1. Load source files
# ----------------------------------------------------------------------
loan = pd.read_csv(SRC / 'auto_loan_securitisation_data.csv', parse_dates=[
    'OriginationDate', 'CutoffDate', 'MaturityDate', 'LastPaymentDate'])
dpd  = pd.read_csv(SRC / 'dpd_snapshot_history.csv',
                   parse_dates=['SnapshotDate', 'LastPaymentDate'])
loss = pd.read_csv(SRC / 'dynamic_loss_monthly.csv',
                   parse_dates=['ReportingDate'])
vint = pd.read_csv(SRC / 'static_pool_vintage_data.csv',
                   parse_dates=['VintageStartDate'])

# ----------------------------------------------------------------------
# 2. dim_calendar – continuous date table 2021-01-01 → 2032-12-31
# ----------------------------------------------------------------------
cal = pd.DataFrame({'Date': pd.date_range('2021-01-01', '2032-12-31', freq='D')})
cal['DateKey']      = cal.Date.dt.strftime('%Y%m%d').astype(int)
cal['Year']         = cal.Date.dt.year
cal['Quarter']      = cal.Date.dt.quarter
cal['Month']        = cal.Date.dt.month
cal['MonthName']    = cal.Date.dt.strftime('%b')
cal['MonthYear']    = cal.Date.dt.strftime('%b-%Y')
cal['YearMonth']    = cal.Date.dt.strftime('%Y-%m')
cal['YearQuarter']  = cal.Year.astype(str) + '-Q' + cal.Quarter.astype(str)
cal['Day']          = cal.Date.dt.day
cal['DayOfWeek']    = cal.Date.dt.dayofweek + 1
cal['DayName']      = cal.Date.dt.strftime('%a')
cal['IsWeekend']    = cal.DayOfWeek.isin([6, 7])
cal['IsMonthEnd']   = cal.Date.dt.is_month_end
cal['IsQuarterEnd'] = cal.Date.dt.is_quarter_end
cal['IsYearEnd']    = cal.Date.dt.is_year_end
# Indian fiscal year: Apr–Mar
cal['FiscalYear']    = np.where(cal.Month >= 4, 'FY' + (cal.Year+1).astype(str).str[-2:],
                                                 'FY' + cal.Year.astype(str).str[-2:])
cal['FiscalQuarter'] = np.where(cal.Month.isin([4,5,6]),     'Q1',
                        np.where(cal.Month.isin([7,8,9]),    'Q2',
                         np.where(cal.Month.isin([10,11,12]),'Q3','Q4')))
cal.to_csv(OUT/'dim_calendar.csv', index=False)
print(f"dim_calendar:     {len(cal):,} rows")

# ----------------------------------------------------------------------
# 3. dim_borrower
# ----------------------------------------------------------------------
def income_band(x):
    if x < 500_000:      return '<5L'
    if x < 1_000_000:    return '5L-10L'
    if x < 2_000_000:    return '10L-20L'
    if x < 5_000_000:    return '20L-50L'
    return '50L+'

def cibil_band(x):
    if x < 600:  return 'Sub-Prime (<600)'
    if x < 650:  return 'Near-Prime (600-649)'
    if x < 700:  return 'Mid-Prime (650-699)'
    if x < 750:  return 'Prime (700-749)'
    if x < 800:  return 'Super-Prime (750-799)'
    return 'Exceptional (800+)'

def age_band(a):
    if a < 30: return '<30'
    if a < 40: return '30-39'
    if a < 50: return '40-49'
    if a < 60: return '50-59'
    return '60+'

dim_bor = loan[['BorrowerID', 'BorrowerAge', 'EmploymentType', 'AnnualIncome_INR',
                'DTI_Ratio', 'CIBIL_Score_Origination', 'CIBIL_Score_Current']].drop_duplicates('BorrowerID').copy()
dim_bor['AgeBand']         = dim_bor.BorrowerAge.apply(age_band)
dim_bor['IncomeBand']      = dim_bor.AnnualIncome_INR.apply(income_band)
dim_bor['CIBILBand_Orig']  = dim_bor.CIBIL_Score_Origination.apply(cibil_band)
dim_bor['CIBILBand_Curr']  = dim_bor.CIBIL_Score_Current.apply(cibil_band)
dim_bor['CIBIL_Drift']     = dim_bor.CIBIL_Score_Current - dim_bor.CIBIL_Score_Origination
dim_bor['DTI_Band']        = pd.cut(dim_bor.DTI_Ratio, bins=[-0.001,0.2,0.35,0.5,1.0],
                                    labels=['Low (<20%)','Moderate (20-35%)','High (35-50%)','Very High (>50%)'])
dim_bor.to_csv(OUT/'dim_borrower.csv', index=False)
print(f"dim_borrower:     {len(dim_bor):,} rows")

# ----------------------------------------------------------------------
# 4. dim_vehicle (one row per make/model/year/type combination)
# ----------------------------------------------------------------------
dim_veh = loan[['VehicleMake','VehicleModel','VehicleYear','VehicleType','IsNewVehicle']].drop_duplicates().reset_index(drop=True)
dim_veh.insert(0, 'VehicleKey', range(1, len(dim_veh)+1))
dim_veh.to_csv(OUT/'dim_vehicle.csv', index=False)
print(f"dim_vehicle:      {len(dim_veh):,} rows")

# ----------------------------------------------------------------------
# 5. dim_geography – Region/State + tier classification
# ----------------------------------------------------------------------
state_tier = {  # rough RBI tier mapping
    'Maharashtra':'Tier-1','Delhi':'Tier-1','Karnataka':'Tier-1','Tamil Nadu':'Tier-1',
    'Telangana':'Tier-1','Gujarat':'Tier-1','West Bengal':'Tier-1','Haryana':'Tier-2',
    'Punjab':'Tier-2','Kerala':'Tier-2','Rajasthan':'Tier-2','Uttar Pradesh':'Tier-2',
    'Andhra Pradesh':'Tier-2','Madhya Pradesh':'Tier-2','Odisha':'Tier-3','Bihar':'Tier-3',
    'Jharkhand':'Tier-3','Chhattisgarh':'Tier-3','Assam':'Tier-3','Goa':'Tier-2',
    'Uttarakhand':'Tier-3','Himachal Pradesh':'Tier-3','Jammu & Kashmir':'Tier-3'
}
dim_geo = loan[['Region','State']].drop_duplicates().reset_index(drop=True)
dim_geo.insert(0, 'GeoKey', range(1, len(dim_geo)+1))
dim_geo['StateTier'] = dim_geo.State.map(state_tier).fillna('Tier-3')
dim_geo['Zone'] = dim_geo.Region
dim_geo.to_csv(OUT/'dim_geography.csv', index=False)
print(f"dim_geography:    {len(dim_geo):,} rows")

# ----------------------------------------------------------------------
# 6. dim_servicer
# ----------------------------------------------------------------------
dim_svc = loan[['ServicerID','ServicerName']].drop_duplicates().reset_index(drop=True)
dim_svc['ServicerType']     = ['Bank','NBFC','Bank']  # SVC001 HDFC=Bank, SVC003 Bajaj=NBFC, ICICI=Bank
# safer: map explicitly
typ_map = {'HDFC Bank Auto Finance':'Bank','Bajaj Finance Auto':'NBFC','ICICI Auto Loans':'Bank'}
dim_svc['ServicerType']     = dim_svc.ServicerName.map(typ_map)
dim_svc['ServicerRating']   = dim_svc.ServicerName.map({
    'HDFC Bank Auto Finance':'AAA',
    'ICICI Auto Loans':'AAA',
    'Bajaj Finance Auto':'AA+'})
dim_svc['BackupServicer']   = 'SBI Cap Trustee'
dim_svc.to_csv(OUT/'dim_servicer.csv', index=False)
print(f"dim_servicer:     {len(dim_svc):,} rows")

# ----------------------------------------------------------------------
# 7. dim_pool – securitisation pool master
# ----------------------------------------------------------------------
pool_bal = loan.OriginalLoanAmount.sum()
dim_pool = pd.DataFrame([{
    'PoolID': 'ZAAUTO2024-1',
    'PoolName': 'Zenith Auto Receivables Trust 2024 Series 1',
    'AssetClass': 'Auto Loan ABS',
    'OriginatorName': 'Zenith Capital Originators Consortium',
    'TrusteeName': 'IDBI Trusteeship Services Ltd',
    'IssueDate': '2024-10-31',
    'CutoffDate': '2024-10-31',
    'LegalMaturity': '2032-12-31',
    'OriginalPoolBalance_INR': pool_bal,
    'CurrentPoolBalance_INR': loan.CurrentBalance.sum(),
    'LoanCount': len(loan),
    'WAC_Pct': round((loan.InterestRate*loan.CurrentBalance).sum()/loan.CurrentBalance.sum(),2),
    'WAM_Months': round((loan.RemainingTerm*loan.CurrentBalance).sum()/loan.CurrentBalance.sum(),2),
    'WALA_Months': round((loan.MonthsOnBook*loan.CurrentBalance).sum()/loan.CurrentBalance.sum(),2),
    'Rating': 'AAA(SO)/AA(SO)/BBB(SO)',
    'Currency': 'INR',
    'Country': 'India',
    'RBI_RegFramework': 'Master Direction – Reserve Bank of India (Securitisation of Standard Assets) Directions, 2021'
}])
dim_pool.to_csv(OUT/'dim_pool.csv', index=False)
print(f"dim_pool:         {len(dim_pool):,} rows")

# ----------------------------------------------------------------------
# 8. dim_tranche – Senior / Mezzanine / Equity
# ----------------------------------------------------------------------
total = pool_bal
dim_tr = pd.DataFrame([
    {'TrancheID':'TR-A','TrancheName':'Class A – Senior','TrancheRank':1,
     'CreditRating':'AAA(SO)','Subordination_Pct':0.20,
     'OriginalBalance_INR': total*0.80, 'CouponRate_Pct': 8.25,
     'EnhancementType':'Subordination + Cash Reserve + Excess Spread',
     'ExpectedAvgLife_Years': 2.1,
     'PrincipalAllocation':'Sequential', 'FirstLossPosition': False},
    {'TrancheID':'TR-B','TrancheName':'Class B – Mezzanine','TrancheRank':2,
     'CreditRating':'AA(SO)','Subordination_Pct':0.08,
     'OriginalBalance_INR': total*0.12, 'CouponRate_Pct': 10.50,
     'EnhancementType':'Subordination + Excess Spread',
     'ExpectedAvgLife_Years': 3.4,
     'PrincipalAllocation':'Sequential', 'FirstLossPosition': False},
    {'TrancheID':'TR-C','TrancheName':'Class C – Equity / Originator Retained','TrancheRank':3,
     'CreditRating':'BBB(SO) / Unrated','Subordination_Pct':0.00,
     'OriginalBalance_INR': total*0.08, 'CouponRate_Pct': 14.00,
     'EnhancementType':'First-loss piece',
     'ExpectedAvgLife_Years': 4.8,
     'PrincipalAllocation':'Residual', 'FirstLossPosition': True},
])
dim_tr.to_csv(OUT/'dim_tranche.csv', index=False)
print(f"dim_tranche:      {len(dim_tr):,} rows")

# ----------------------------------------------------------------------
# 9. dim_investor – investors per tranche
# ----------------------------------------------------------------------
investors = pd.DataFrame([
    # Senior Class A
    {'InvestorID':'INV-001','InvestorName':'LIC of India','InvestorType':'Insurance',
     'Country':'India','TrancheID':'TR-A','Allocation_Pct':0.40},
    {'InvestorID':'INV-002','InvestorName':'SBI Mutual Fund – Debt','InvestorType':'Asset Manager',
     'Country':'India','TrancheID':'TR-A','Allocation_Pct':0.25},
    {'InvestorID':'INV-003','InvestorName':'HDFC Pension Fund','InvestorType':'Pension Fund',
     'Country':'India','TrancheID':'TR-A','Allocation_Pct':0.20},
    {'InvestorID':'INV-004','InvestorName':'Nomura Asset Mgmt','InvestorType':'Foreign Portfolio Investor',
     'Country':'Japan','TrancheID':'TR-A','Allocation_Pct':0.15},
    # Mezz Class B
    {'InvestorID':'INV-005','InvestorName':'ICICI Prudential AMC','InvestorType':'Asset Manager',
     'Country':'India','TrancheID':'TR-B','Allocation_Pct':0.50},
    {'InvestorID':'INV-006','InvestorName':'Edelweiss Alternative Asset','InvestorType':'AIF',
     'Country':'India','TrancheID':'TR-B','Allocation_Pct':0.30},
    {'InvestorID':'INV-007','InvestorName':'Goldman Sachs Asia Credit','InvestorType':'Foreign Portfolio Investor',
     'Country':'USA','TrancheID':'TR-B','Allocation_Pct':0.20},
    # Equity Class C (originator retained for skin-in-the-game)
    {'InvestorID':'INV-008','InvestorName':'Zenith Capital (Originator MRR)','InvestorType':'Originator',
     'Country':'India','TrancheID':'TR-C','Allocation_Pct':1.00},
])
investors = investors.merge(dim_tr[['TrancheID','OriginalBalance_INR']], on='TrancheID')
investors['InvestedAmount_INR'] = (investors.Allocation_Pct * investors.OriginalBalance_INR).round(2)
investors.drop(columns='OriginalBalance_INR', inplace=True)
investors.to_csv(OUT/'dim_investor.csv', index=False)
print(f"dim_investor:     {len(investors):,} rows")

# ----------------------------------------------------------------------
# 10. dim_scenario – stress-testing scenarios
# ----------------------------------------------------------------------
scenarios = pd.DataFrame([
    {'ScenarioID':'BASE','ScenarioName':'Baseline','ScenarioType':'Base',
     'PD_Multiplier':1.00,'LGD_Multiplier':1.00,'Recovery_Haircut_Pct':0.00,
     'UnemploymentShock_Pct':0.0,'InterestRateShock_bps':0,
     'VehicleValueShock_Pct':0.00,'GDP_Shock_Pct':0.0,'Inflation_Shock_Pct':0.0,
     'Description':'Through-the-cycle baseline. IFRS 9 12-month ECL for Stage 1; lifetime ECL for Stages 2-3.'},
    {'ScenarioID':'MILD','ScenarioName':'Mild Slowdown','ScenarioType':'Mild',
     'PD_Multiplier':1.30,'LGD_Multiplier':1.10,'Recovery_Haircut_Pct':0.10,
     'UnemploymentShock_Pct':1.5,'InterestRateShock_bps':75,
     'VehicleValueShock_Pct':0.07,'GDP_Shock_Pct':-1.0,'Inflation_Shock_Pct':1.5,
     'Description':'Mild GDP slowdown 1pp; 75 bps RBI hike; modest vehicle value compression.'},
    {'ScenarioID':'MODERATE','ScenarioName':'Moderate Recession','ScenarioType':'Moderate',
     'PD_Multiplier':1.80,'LGD_Multiplier':1.25,'Recovery_Haircut_Pct':0.20,
     'UnemploymentShock_Pct':3.0,'InterestRateShock_bps':150,
     'VehicleValueShock_Pct':0.15,'GDP_Shock_Pct':-2.5,'Inflation_Shock_Pct':3.0,
     'Description':'2014-style EM correction. Used-car index down 15%. Self-employed segment under pressure.'},
    {'ScenarioID':'SEVERE','ScenarioName':'Severe Recession','ScenarioType':'Severe',
     'PD_Multiplier':2.80,'LGD_Multiplier':1.45,'Recovery_Haircut_Pct':0.35,
     'UnemploymentShock_Pct':5.5,'InterestRateShock_bps':250,
     'VehicleValueShock_Pct':0.25,'GDP_Shock_Pct':-4.5,'Inflation_Shock_Pct':5.0,
     'Description':'2008-GFC analogue. Sharp default rise across all stages; severe LGD on commercial vehicles.'},
    {'ScenarioID':'CRISIS','ScenarioName':'Tail Crisis (IL&FS / COVID combo)','ScenarioType':'Tail',
     'PD_Multiplier':4.50,'LGD_Multiplier':1.75,'Recovery_Haircut_Pct':0.50,
     'UnemploymentShock_Pct':8.0,'InterestRateShock_bps':350,
     'VehicleValueShock_Pct':0.40,'GDP_Shock_Pct':-7.0,'Inflation_Shock_Pct':7.5,
     'Description':'NBFC liquidity crisis + pandemic-style demand shock. Used-vehicle prices collapse; repo logistics frozen.'},
])
scenarios.to_csv(OUT/'dim_scenario.csv', index=False)
print(f"dim_scenario:     {len(scenarios):,} rows")

# ----------------------------------------------------------------------
# 11. dim_economic_indicator (definitions)
# ----------------------------------------------------------------------
indicators = pd.DataFrame([
    {'IndicatorCode':'GDP_GR','IndicatorName':'India Real GDP Growth (YoY %)','Source':'MoSPI','Frequency':'Quarterly'},
    {'IndicatorCode':'CPI_INF','IndicatorName':'India CPI Inflation (YoY %)','Source':'MoSPI','Frequency':'Monthly'},
    {'IndicatorCode':'REPO','IndicatorName':'RBI Repo Rate (%)','Source':'RBI','Frequency':'Policy Decision'},
    {'IndicatorCode':'UNEMP','IndicatorName':'Urban Unemployment (CMIE, %)','Source':'CMIE','Frequency':'Monthly'},
    {'IndicatorCode':'IIP','IndicatorName':'Index of Industrial Production (YoY %)','Source':'MoSPI','Frequency':'Monthly'},
    {'IndicatorCode':'AUTO_SALES','IndicatorName':'PV Domestic Sales (YoY %)','Source':'SIAM','Frequency':'Monthly'},
    {'IndicatorCode':'USED_PR_IDX','IndicatorName':'Used Vehicle Price Index (proxy)','Source':'Synthetic','Frequency':'Monthly'},
    {'IndicatorCode':'INR_USD','IndicatorName':'INR/USD','Source':'RBI','Frequency':'Monthly'},
])
indicators.to_csv(OUT/'dim_economic_indicator.csv', index=False)
print(f"dim_economic_indicator: {len(indicators):,} rows")

# ----------------------------------------------------------------------
# 12. fact_economic_history – plausible monthly time series 2021-2024
# ----------------------------------------------------------------------
months = pd.date_range('2021-01-31','2024-12-31',freq='ME')
np.random.seed(7)
econ_rows = []
for d in months:
    yr = d.year
    # Approx realistic India macro path
    gdp = {2021:8.0, 2022:7.2, 2023:7.6, 2024:7.0}[yr] + np.random.normal(0,0.4)
    cpi = {2021:5.1, 2022:6.7, 2023:5.4, 2024:4.8}[yr] + np.random.normal(0,0.3)
    repo= {2021:4.00,2022:5.40,2023:6.50,2024:6.50}[yr]
    une = {2021:7.5, 2022:7.2, 2023:7.0, 2024:7.1}[yr] + np.random.normal(0,0.3)
    iip = {2021:11.4,2022:5.2, 2023:5.8, 2024:5.5}[yr] + np.random.normal(0,1.0)
    aut = {2021:4.6, 2022:23.1,2023:8.4, 2024:3.5}[yr] + np.random.normal(0,2.0)
    upi = 100 + (d.year-2021)*4 + (d.month/12)*1.0 + np.random.normal(0,0.5)
    fx  = {2021:74.5,2022:80.4,2023:82.5,2024:83.5}[yr] + np.random.normal(0,0.4)
    for code,val in [('GDP_GR',gdp),('CPI_INF',cpi),('REPO',repo),('UNEMP',une),
                     ('IIP',iip),('AUTO_SALES',aut),('USED_PR_IDX',upi),('INR_USD',fx)]:
        econ_rows.append({'ReportingDate':d.strftime('%Y-%m-%d'),
                          'IndicatorCode':code,'Value':round(val,2)})
econ = pd.DataFrame(econ_rows)
econ.to_csv(OUT/'fact_economic_history.csv', index=False)
print(f"fact_economic_history: {len(econ):,} rows")

# ----------------------------------------------------------------------
# 13. fact_loan – curated wrapper, surrogate keys
# ----------------------------------------------------------------------
loan_f = loan.copy()
loan_f = loan_f.merge(dim_geo[['Region','State','GeoKey']], on=['Region','State'], how='left')
loan_f = loan_f.merge(dim_veh, on=['VehicleMake','VehicleModel','VehicleYear','VehicleType','IsNewVehicle'], how='left')
loan_f['OriginationDateKey'] = loan_f.OriginationDate.dt.strftime('%Y%m%d').astype(int)
loan_f['CutoffDateKey']      = loan_f.CutoffDate.dt.strftime('%Y%m%d').astype(int)
loan_f['MaturityDateKey']    = loan_f.MaturityDate.dt.strftime('%Y%m%d').astype(int)
loan_f['VintageID']          = loan_f.OriginationDate.dt.year.astype(str)+'-Q'+loan_f.OriginationDate.dt.quarter.astype(str)
# Derived analytic columns
loan_f['LTV_Band']      = pd.cut(loan_f.LTV_Current, bins=[-.001,0.4,0.6,0.8,1.0,2.0],
                                 labels=['<40%','40-60%','60-80%','80-100%','>100%'])
loan_f['Balance_Band']  = pd.cut(loan_f.CurrentBalance, bins=[-.01,250_000,500_000,750_000,1_000_000,1e9],
                                 labels=['<2.5L','2.5-5L','5-7.5L','7.5-10L','>10L'])
loan_f['DPD_Bucket']    = loan_f.DelinquencyStatus
loan_f['Stage_Label']   = loan_f.IFRS9_Stage.map({1:'Stage 1 – Performing',
                                                  2:'Stage 2 – SICR',
                                                  3:'Stage 3 – Credit-Impaired'})
loan_f['RBI_Asset_Class'] = np.where(loan_f.DelinquencyDays==0,'Standard',
                              np.where(loan_f.DelinquencyDays<=30,'SMA-0',
                               np.where(loan_f.DelinquencyDays<=60,'SMA-1',
                                np.where(loan_f.DelinquencyDays<=90,'SMA-2','NPA'))))
loan_f.to_csv(OUT/'fact_loan.csv', index=False)
print(f"fact_loan:        {len(loan_f):,} rows")

# ----------------------------------------------------------------------
# 14. fact_dpd_snapshot – pass through with surrogate keys
# ----------------------------------------------------------------------
dpd_f = dpd.copy()
dpd_f['SnapshotDateKey'] = dpd_f.SnapshotDate.dt.strftime('%Y%m%d').astype(int)
dpd_f.to_csv(OUT/'fact_dpd_snapshot.csv', index=False)
print(f"fact_dpd_snapshot:{len(dpd_f):,} rows")

# ----------------------------------------------------------------------
# 15. fact_loss_monthly – pass through
# ----------------------------------------------------------------------
loss_f = loss.copy()
loss_f['ReportingDateKey'] = loss_f.ReportingDate.dt.strftime('%Y%m%d').astype(int)
loss_f.to_csv(OUT/'fact_loss_monthly.csv', index=False)
print(f"fact_loss_monthly:{len(loss_f):,} rows")

# ----------------------------------------------------------------------
# 16. fact_vintage – pass through
# ----------------------------------------------------------------------
vint_f = vint.copy()
vint_f['VintageStartDateKey'] = vint_f.VintageStartDate.dt.strftime('%Y%m%d').astype(int)
vint_f.to_csv(OUT/'fact_vintage.csv', index=False)
print(f"fact_vintage:     {len(vint_f):,} rows")

# ----------------------------------------------------------------------
# 17. fact_tranche_cashflow – sequential-pay waterfall over reporting months
# ----------------------------------------------------------------------
months_l = pd.to_datetime(loss.ReportingDate).sort_values().tolist()
tr = dim_tr.set_index('TrancheID').to_dict('index')
rows = []
bal_A = tr['TR-A']['OriginalBalance_INR']
bal_B = tr['TR-B']['OriginalBalance_INR']
bal_C = tr['TR-C']['OriginalBalance_INR']
for _, l in loss.iterrows():
    d = l.ReportingDate
    avail_int = l.BillingAmount - l.NetLoss_ThisMonth + l.ExcessSpread_Monthly
    avail_prin = l.Prepayments_ThisMonth + l.ScheduledAmort
    # Interest waterfall (sequential by rank)
    int_A = bal_A * tr['TR-A']['CouponRate_Pct']/100/12
    int_B = bal_B * tr['TR-B']['CouponRate_Pct']/100/12
    int_C = max(avail_int - int_A - int_B, 0)
    # Principal waterfall (turbo to A, then B, then C residual)
    prin_A = min(avail_prin, bal_A)
    prin_B = min(max(avail_prin - prin_A, 0), bal_B)
    prin_C = max(avail_prin - prin_A - prin_B, 0)
    # Losses absorbed bottom-up (C → B → A)
    loss_left = l.NetLoss_ThisMonth
    loss_C = min(loss_left, bal_C); loss_left -= loss_C
    loss_B = min(loss_left, bal_B); loss_left -= loss_B
    loss_A = min(loss_left, bal_A)
    # Update balances
    new_A = max(bal_A - prin_A - loss_A, 0)
    new_B = max(bal_B - prin_B - loss_B, 0)
    new_C = max(bal_C - prin_C - loss_C, 0)
    rows.append({'ReportingDate':d.strftime('%Y-%m-%d'),'TrancheID':'TR-A',
                 'BOP_Balance':bal_A,'InterestPaid':int_A,'PrincipalPaid':prin_A,
                 'LossAllocated':loss_A,'EOP_Balance':new_A})
    rows.append({'ReportingDate':d.strftime('%Y-%m-%d'),'TrancheID':'TR-B',
                 'BOP_Balance':bal_B,'InterestPaid':int_B,'PrincipalPaid':prin_B,
                 'LossAllocated':loss_B,'EOP_Balance':new_B})
    rows.append({'ReportingDate':d.strftime('%Y-%m-%d'),'TrancheID':'TR-C',
                 'BOP_Balance':bal_C,'InterestPaid':int_C,'PrincipalPaid':prin_C,
                 'LossAllocated':loss_C,'EOP_Balance':new_C})
    bal_A, bal_B, bal_C = new_A, new_B, new_C
tcf = pd.DataFrame(rows)
tcf.to_csv(OUT/'fact_tranche_cashflow.csv', index=False)
print(f"fact_tranche_cashflow: {len(tcf):,} rows")

# ----------------------------------------------------------------------
# 18. fact_waterfall_distribution – simplified line-item waterfall
# ----------------------------------------------------------------------
wf_rows = []
for _, l in loss.iterrows():
    d = l.ReportingDate.strftime('%Y-%m-%d')
    coll = l.CollectionsTotal
    rev = coll  # Available revenue waterfall
    items = [
        ('1. Total Collections',                rev),
        ('2. Servicer Fee (0.50% p.a. on EOP)',-l.EOP_Balance*0.005/12),
        ('3. Trustee Fee (₹2L/month flat)',    -200_000),
        ('4. Class A Interest',                -tcf.loc[(tcf.ReportingDate==d)&(tcf.TrancheID=='TR-A'),'InterestPaid'].iloc[0]),
        ('5. Class A Principal',               -tcf.loc[(tcf.ReportingDate==d)&(tcf.TrancheID=='TR-A'),'PrincipalPaid'].iloc[0]),
        ('6. Class B Interest',                -tcf.loc[(tcf.ReportingDate==d)&(tcf.TrancheID=='TR-B'),'InterestPaid'].iloc[0]),
        ('7. Class B Principal',               -tcf.loc[(tcf.ReportingDate==d)&(tcf.TrancheID=='TR-B'),'PrincipalPaid'].iloc[0]),
        ('8. Replenishment of Cash Reserve',   -50_000),
        ('9. Class C / Residual to Equity',    -l.ExcessSpread_Monthly),
    ]
    for label, amt in items:
        wf_rows.append({'ReportingDate':d,'Step':label,'Amount':round(amt,2)})
wf = pd.DataFrame(wf_rows)
wf.to_csv(OUT/'fact_waterfall_distribution.csv', index=False)
print(f"fact_waterfall_distribution: {len(wf):,} rows")

# ----------------------------------------------------------------------
# 19. fact_stress_results – apply each scenario to current loan portfolio
# ----------------------------------------------------------------------
stress_rows = []
for _, s in scenarios.iterrows():
    pd_adj   = (loan.PD_Estimate  * s.PD_Multiplier).clip(upper=1.0)
    lgd_adj  = (loan.LGD_Estimate * s.LGD_Multiplier * (1+s.Recovery_Haircut_Pct)).clip(upper=1.0)
    ecl_adj  = pd_adj * lgd_adj * loan.EAD
    coll_haircut = s.VehicleValueShock_Pct  # vehicle value drop reduces recoveries
    new_ltv = loan.LTV_Current / (1 - s.VehicleValueShock_Pct)
    for st in [1,2,3]:
        msk = loan.IFRS9_Stage==st
        stress_rows.append({
            'ScenarioID':s.ScenarioID,
            'Stage':st,
            'LoanCount':int(msk.sum()),
            'Exposure_INR':float(loan.loc[msk,'EAD'].sum()),
            'ECL_Baseline_INR':float(loan.loc[msk,'ECL_Provision'].sum()),
            'ECL_Stressed_INR':float(ecl_adj[msk].sum()),
            'ECL_Increase_INR':float(ecl_adj[msk].sum() - loan.loc[msk,'ECL_Provision'].sum()),
            'AvgPD_Stressed':float(pd_adj[msk].mean()),
            'AvgLGD_Stressed':float(lgd_adj[msk].mean()),
            'AvgLTV_Stressed':float(new_ltv[msk].mean()),
        })
    # Tranche-level loss allocation under stress
    total_stressed_loss = float(ecl_adj.sum())
    rem_loss = total_stressed_loss
    c_loss = min(rem_loss, dim_tr.iloc[2].OriginalBalance_INR); rem_loss -= c_loss
    b_loss = min(rem_loss, dim_tr.iloc[1].OriginalBalance_INR); rem_loss -= b_loss
    a_loss = min(rem_loss, dim_tr.iloc[0].OriginalBalance_INR)
    stress_rows.append({'ScenarioID':s.ScenarioID,'Stage':'TR-A','LoanCount':None,
                        'Exposure_INR':float(dim_tr.iloc[0].OriginalBalance_INR),
                        'ECL_Baseline_INR':0,'ECL_Stressed_INR':a_loss,
                        'ECL_Increase_INR':a_loss,'AvgPD_Stressed':None,
                        'AvgLGD_Stressed':None,'AvgLTV_Stressed':None})
    stress_rows.append({'ScenarioID':s.ScenarioID,'Stage':'TR-B','LoanCount':None,
                        'Exposure_INR':float(dim_tr.iloc[1].OriginalBalance_INR),
                        'ECL_Baseline_INR':0,'ECL_Stressed_INR':b_loss,
                        'ECL_Increase_INR':b_loss,'AvgPD_Stressed':None,
                        'AvgLGD_Stressed':None,'AvgLTV_Stressed':None})
    stress_rows.append({'ScenarioID':s.ScenarioID,'Stage':'TR-C','LoanCount':None,
                        'Exposure_INR':float(dim_tr.iloc[2].OriginalBalance_INR),
                        'ECL_Baseline_INR':0,'ECL_Stressed_INR':c_loss,
                        'ECL_Increase_INR':c_loss,'AvgPD_Stressed':None,
                        'AvgLGD_Stressed':None,'AvgLTV_Stressed':None})
st_df = pd.DataFrame(stress_rows)
st_df.to_csv(OUT/'fact_stress_results.csv', index=False)
print(f"fact_stress_results:  {len(st_df):,} rows")

# ----------------------------------------------------------------------
# 20. Summary
# ----------------------------------------------------------------------
print("\n" + "="*60)
print("ALL DATA TABLES BUILT")
print("="*60)
for f in sorted(OUT.glob('*.csv')):
    print(f"  {f.name:42s} {f.stat().st_size/1024:>10.1f} KB")
