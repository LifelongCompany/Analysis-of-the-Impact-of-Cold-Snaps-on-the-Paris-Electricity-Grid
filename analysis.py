import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from sklearn.linear_model import LinearRegression
import numpy as np

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 300

def load_and_clean_data():
    print("Loading data...")

    # 1. Eco2Mix (National Generation)
    eco_df = pd.read_csv('data/eco2mix-national-cons-def.csv', sep=';')

    # Manually convert Date
    eco_df['Date'] = pd.to_datetime(eco_df['Date'], format='%Y-%m-%d')

    # Filter for January 2024
    eco_df = eco_df[eco_df['Date'].dt.year == 2024]
    eco_df = eco_df[eco_df['Date'].dt.month == 1]

    # Drop rows with missing Consommation (which are the 15-min fillers)
    eco_df = eco_df.dropna(subset=['Consommation (MW)'])

    # Create 'Thermal' category
    eco_df['Fioul (MW)'] = eco_df['Fioul (MW)'].fillna(0)
    eco_df['Charbon (MW)'] = eco_df['Charbon (MW)'].fillna(0)
    eco_df['Gaz (MW)'] = eco_df['Gaz (MW)'].fillna(0)
    eco_df['Thermal (MW)'] = eco_df['Fioul (MW)'] + eco_df['Charbon (MW)'] + eco_df['Gaz (MW)']

    # Handle Bioenergies if missing
    if 'Bioénergies (MW)' in eco_df.columns:
        eco_df['Bioénergies (MW)'] = eco_df['Bioénergies (MW)'].fillna(0)

    # Create DateTime column
    eco_df['DateTime'] = pd.to_datetime(eco_df['Date'].astype(str) + ' ' + eco_df['Heure'])

    # 2. Pic Journalier (National Peak Load & Temp)
    pic_df = pd.read_csv('data/pic-journalier-consommation-brute.csv', sep=';')
    pic_df['Date'] = pd.to_datetime(pic_df['Date'], format='%Y-%m-%d')

    pic_df = pic_df[pic_df['Date'].dt.year == 2024]
    pic_df = pic_df[pic_df['Date'].dt.month == 1]
    pic_df = pic_df.sort_values('Date')

    # 3. ParisTEMP (Local Weather)
    paris_df = pd.read_csv('data/ParisTEMP.csv', sep=',')
    paris_df['date'] = pd.to_datetime(paris_df['date'])

    paris_df = paris_df[paris_df['date'].dt.year == 2024]
    paris_df = paris_df[paris_df['date'].dt.month == 1]
    paris_df = paris_df.sort_values('date')

    print("Data loaded successfully.")
    return eco_df, pic_df, paris_df

def step_a_cold_wave(pic_df, paris_df):
    """
    Step A: Cold Wave Identification.
    Plot National Weighted Temp vs Paris Min Temp.
    """
    print("Generating Step A: Cold Wave Identification...")

    # Merge dataframes on Date
    # Rename 'date' in paris_df to 'Date' for easy merging or just plot directly

    plt.figure(figsize=(12, 6))

    # Plot National Weighted Temperature
    plt.plot(pic_df['Date'], pic_df['Température moyenne (°C)'],
             label='National Weighted Temp (Avg)', marker='o', linewidth=2, color='navy')

    # Plot Paris Min Temperature
    # Ensure dates align. We can merge or just plot x=date, y=tmin
    plt.plot(paris_df['date'], paris_df['tmin'],
             label='Paris Min Temp', marker='s', linewidth=2, color='teal', linestyle='--')

    # Highlight Cold Wave Window (Jan 8 - Jan 15)
    start_date = pd.to_datetime('2024-01-08')
    end_date = pd.to_datetime('2024-01-15')

    plt.axvspan(start_date, end_date, color='skyblue', alpha=0.3, label='Cold Wave (Jan 8-15)')

    # Formatting
    plt.title('Step A: Temperature Profile - January 2024 Cold Wave', fontsize=16)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.xlabel('Date', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    # Set x-axis format
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xlim(pd.to_datetime('2024-01-01'), pd.to_datetime('2024-01-31'))

    plt.tight_layout()
    plt.savefig('01_temperature_profile.png')
    print("Saved 01_temperature_profile.png")
    plt.close()

def step_b_thermosensitivity(pic_df):
    """
    Step B: Thermosensitivity Analysis.
    Linear Regression: Load ~ Temp.
    """
    print("Generating Step B: Thermosensitivity Analysis...")

    # Clean data for regression
    reg_df = pic_df[['Température moyenne (°C)', 'Pic journalier consommation (MW)']].dropna()

    X = reg_df['Température moyenne (°C)'].values.reshape(-1, 1)
    y = reg_df['Pic journalier consommation (MW)'].values

    # Fit model
    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0] # MW/°C
    intercept = model.intercept_
    r_squared = model.score(X, y)

    gradient_gw = slope / 1000 # GW/°C

    print(f"Gradient: {gradient_gw:.2f} GW/°C")
    print(f"Intercept: {intercept:.2f} MW")
    print(f"R^2: {r_squared:.2f}")

    # Plot
    plt.figure(figsize=(10, 6))

    # Scatter plot
    sns.scatterplot(x='Température moyenne (°C)', y='Pic journalier consommation (MW)', data=reg_df,
                    color='crimson', s=100, label='Daily Peak Load')

    # Regression line
    X_range = np.linspace(reg_df['Température moyenne (°C)'].min(), reg_df['Température moyenne (°C)'].max(), 100).reshape(-1, 1)
    y_pred = model.predict(X_range)

    plt.plot(X_range, y_pred, color='navy', linewidth=2, label=f'Regression Line (Gradient: {gradient_gw:.2f} GW/°C)')

    # Formatting
    plt.title('Step B: Thermosensitivity of French Power Demand (Jan 2024)', fontsize=16)
    plt.xlabel('National Weighted Temperature (°C)', fontsize=12)
    plt.ylabel('Daily Peak Load (MW)', fontsize=12)

    # Invert X axis

    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    # Add text box with equation
    text_str = f'Load = {gradient_gw:.2f} * T + {intercept/1000:.2f} GW\n$R^2$ = {r_squared:.2f}'
    plt.text(0.05, 0.95, text_str, transform=plt.gca().transAxes, fontsize=12,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig('02_thermosensitivity_regression.png')
    print("Saved 02_thermosensitivity_regression.png")
    plt.close()

def step_c_supply_mix(eco_df):
    """
    Step C: Supply Mix & "Dunkelflaute".
    Stacked Area Chart and Peak Hour Analysis.
    """
    print("Generating Step C: Supply Mix Analysis...")

    # Filter for Jan 8 - Jan 15
    mask = (eco_df['Date'] >= '2024-01-08') & (eco_df['Date'] <= '2024-01-15')
    mix_df = eco_df.loc[mask].copy()
    mix_df = mix_df.sort_values('DateTime')

    # Define generation columns
    gen_cols = ['Nucléaire (MW)', 'Hydraulique (MW)', 'Bioénergies (MW)',
                'Eolien (MW)', 'Solaire (MW)', 'Thermal (MW)']
    labels = ['Nuclear', 'Hydro', 'Bioenergies', 'Wind', 'Solar', 'Thermal (Fossil)']
    colors = ['#FFD700', '#1E90FF', '#228B22', '#00CED1', '#FFA500', '#A52A2A'] # Gold, DodgerBlue, ForestGreen, DarkTurquoise, Orange, Brown

    plt.figure(figsize=(14, 7))

    # Stacked Area Chart
    plt.stackplot(mix_df['DateTime'],
                  mix_df[gen_cols[0]], mix_df[gen_cols[1]], mix_df[gen_cols[2]],
                  mix_df[gen_cols[3]], mix_df[gen_cols[4]], mix_df[gen_cols[5]],
                  labels=labels, colors=colors, alpha=0.8)

    # Plot Consumption
    plt.plot(mix_df['DateTime'], mix_df['Consommation (MW)'],
             color='black', linewidth=2, linestyle='--', label='National Load')

    # Formatting
    plt.title('Step C: French Power Generation Mix - Cold Wave (Jan 8 - Jan 15)', fontsize=16)
    plt.ylabel('Power (MW)', fontsize=12)
    plt.xlabel('Date / Time', fontsize=12)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(True, linestyle='--', alpha=0.5)

    # Set x-axis format
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b %Hh'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))

    plt.tight_layout()
    plt.savefig('03_generation_stack_jan_cold_wave.png')
    print("Saved 03_generation_stack_jan_cold_wave.png")
    plt.close()

    # "Dunkelflaute" Analysis for Jan 10th Peak
    jan10_df = mix_df[mix_df['Date'] == '2024-01-10']
    peak_row = jan10_df.loc[jan10_df['Consommation (MW)'].idxmax()]

    print("\n--- Dunkelflaute Analysis (Jan 10th Peak) ---")
    print(f"Peak Time: {peak_row['DateTime']}")
    print(f"Peak Load: {peak_row['Consommation (MW)']:.2f} MW")

    wind_solar = peak_row['Eolien (MW)'] + peak_row['Solaire (MW)']
    ws_share = (wind_solar / peak_row['Consommation (MW)']) * 100

    print(f"Wind + Solar Generation: {wind_solar:.2f} MW")
    print(f"Wind + Solar Share: {ws_share:.2f}%")
    print(f"Thermal Generation: {peak_row['Thermal (MW)']:.2f} MW")
    print(f"Imports (approx Load - Gen): {peak_row['Consommation (MW)'] - (peak_row[gen_cols].sum()):.2f} MW")
    print("---------------------------------------------")

def step_d_local_stress(paris_df):
    """
    Step D: Micro Impact - Local Grid Stress.
    Paris Temperature Range (Tmin to Tmax) and Risk Analysis.
    """
    print("Generating Step D: Local Grid Stress Analysis...")

    plt.figure(figsize=(12, 6))

    # Iterate through days to identify risk
    risk_days = []

    for idx, row in paris_df.iterrows():
        tmin = row['tmin']
        tmax = row['tmax']
        tavg = row['tavg']
        date = row['date']

        # Condition A: Freeze/Thaw (Min < 0, Max > 0)
        cond_a = (tmin < 0) and (tmax > 0)

        # Condition B: Icing Risk (-2 <= Mean <= 2 OR Range within [-2, 2])
        # "Temperature range falls within -2 to +2" implies tmin >= -2 and tmax <= 2
        cond_b = (-2 <= tavg <= 2) or (tmin >= -2 and tmax <= 2)

        color = 'gray'
        label = None
        if cond_a or cond_b:
            color = 'orangered'
            risk_days.append(date)
            # Only label "Risk Day" once for legend
            if 'Risk Day' not in plt.gca().get_legend_handles_labels()[1]:
                label = 'Risk Day (Freeze/Thaw or Icing)'

        plt.vlines(x=date, ymin=tmin, ymax=tmax, color=color, linewidth=4, label=label if label else "")
        plt.scatter(date, tavg, color='black', s=15, zorder=5) # Mark average

    # Plot formatting
    plt.axhline(0, color='blue', linestyle='--', linewidth=1, alpha=0.7, label='Freezing Point (0°C)')
    plt.axhspan(-2, 2, color='lightblue', alpha=0.2, label='Icing Risk Zone (-2 to +2°C)')

    plt.title('Step D: Paris Local Grid Stress - Temperature Range (Jan 2024)', fontsize=16)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.xlabel('Date', fontsize=12)

    # Custom legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right')

    plt.grid(True, linestyle='--', alpha=0.5)

    # Set x-axis format
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
    plt.xlim(pd.to_datetime('2024-01-01'), pd.to_datetime('2024-01-31'))

    plt.tight_layout()
    plt.savefig('04_paris_local_stress.png')
    print("Saved 04_paris_local_stress.png")
    plt.close()

    print(f"Identified Risk Days: {[d.strftime('%Y-%m-%d') for d in risk_days]}")

if __name__ == "__main__":
    eco_df, pic_df, paris_df = load_and_clean_data()

    step_a_cold_wave(pic_df, paris_df)
    step_b_thermosensitivity(pic_df)
    step_c_supply_mix(eco_df)
    step_d_local_stress(paris_df)
