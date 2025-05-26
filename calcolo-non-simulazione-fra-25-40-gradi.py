!pip install pvlib
!pip install solarfactors

import pandas as pd
from pvlib import location
from pvlib.bifacial.pvfactors import pvfactors_timeseries
import matplotlib.pyplot as plt
import warnings
from IPython.display import display # Per una migliore visualizzazione delle tabelle in Colab

# supressing shapely warnings that occur on import of pvfactors
warnings.filterwarnings(action='ignore', module='pvfactors')

# %%
# --- PARAMETRI DI SIMULAZIONE E LUOGO ---

# Periodo di simulazione: Un anno intero
times = pd.date_range('2021-01-01', '2022-01-01', freq='1H', tz='Europe/Rome', inclusive='left')

loc = location.Location(latitude=45.12, longitude=9.21, tz=times.tz)
sp = loc.get_solarposition(times)
cs = loc.get_clearsky(times) # Per semplicità usiamo il cielo sereno, ma si potrebbe usare un file TMY per dati reali.

# --- GEOMETRIA DELL'ARRAY PV FISSA ---
pvrow_height = 2
pvrow_width = 8
pitch = 5
gcr = pvrow_width / pitch
axis_azimuth = 180 # Orientamento dell'asse di rotazione, 90 gradi rispetto a surface_azimuth per fisso
surface_azimuth = 180 # Orientamento dei moduli: Sud
albedo = 0.2

# --- PARAMETRI DEL SISTEMA PV PER IL CALCOLO DELLA PRODUZIONE ---
system_total_area_front_side_m2 = 50.0 * 3.75 # Area totale frontale attiva di tutti i moduli PV del tuo impianto in m^2.
module_efficiency = 0.22                # Efficienza complessiva del modulo (es. 20% = 0.20)
bifaciality_factor = 0.60               # Fattore di bifacialità (es. 0.70 significa che la parte posteriore è efficace al 70% rispetto a quella anteriore)

# Intervallo di tempo in ore (freq='1H' significa 1 ora)
time_interval_hours = (times[1] - times[0]).total_seconds() / 3600

# --- RANGE DI TILT DA ANALIZZARE ---
tilt_range = range(25, 41) # Da 25 a 40 gradi inclusi

# Lista per immagazzinare i risultati annuali per ogni tilt
annual_production_results = []

print(f"Inizio simulazioni per i tilt da {tilt_range[0]} a {tilt_range[-1]} gradi...")

# %%
# --- INIZIO CICLO DI ITERAZIONE PER OGNI ANGOLO DI TILT ---
for current_tilt in tilt_range:
    print(f"Simulazione per Tilt: {current_tilt}°...")

    # Esegui la simulazione dell'irradianza con pvfactors per il tilt corrente
    irrad_data = pvfactors_timeseries(
        solar_azimuth=sp['azimuth'],
        solar_zenith=sp['apparent_zenith'],
        surface_azimuth=surface_azimuth,
        surface_tilt=current_tilt, # QUI CAMBIA IL TILT AD OGNI ITERAZIONE
        axis_azimuth=axis_azimuth,
        timestamps=times,
        dni=cs['dni'],
        dhi=cs['dhi'],
        gcr=gcr,
        pvrow_height=pvrow_height,
        pvrow_width=pvrow_width,
        albedo=albedo,
        n_pvrows=3,
        index_observed_pvrow=1
    )

    # Converti i risultati in un Pandas DataFrame
    irrad = pd.concat(irrad_data, axis=1)

    # Ottieni i valori di irradianza assorbita (W/m^2)
    absorbed_irradiance_front = irrad['total_abs_front']
    absorbed_irradiance_back = irrad['total_abs_back']

    # --- CALCOLO PER IMPIANTO BIFACCIALE ---
    effective_power_density_wpm2_bifacial = (absorbed_irradiance_front +
                                             absorbed_irradiance_back * bifaciality_factor)
    system_ac_power_w_bifacial = effective_power_density_wpm2_bifacial * system_total_area_front_side_m2 * module_efficiency
    energy_kwh_per_interval_bifacial = system_ac_power_w_bifacial / 1000 * time_interval_hours
    total_annual_bifacial_kwh = energy_kwh_per_interval_bifacial.sum()

    # --- CALCOLO PER IMPIANTO MONOFACCIALE ---
    effective_power_density_wpm2_monofacial = absorbed_irradiance_front
    system_ac_power_w_monofacial = effective_power_density_wpm2_monofacial * system_total_area_front_side_m2 * module_efficiency
    energy_kwh_per_interval_monofacial = system_ac_power_w_monofacial / 1000 * time_interval_hours
    total_annual_monofacial_kwh = energy_kwh_per_interval_monofacial.sum()

    # Salva i risultati per questo tilt
    annual_production_results.append({
        'Tilt_Degrees': current_tilt,
        'Bifacial_Annual_kWh': total_annual_bifacial_kwh,
        'Monofacial_Annual_kWh': total_annual_monofacial_kwh
    })

print("\n--- Simulazioni completate! ---")

# %%
# --- ANALISI E STAMPA DEI RISULTATI FINALI ---

results_df = pd.DataFrame(annual_production_results)

print("\n--- Riepilogo dei Parametri del Sistema ---")
print(f"Area totale del sistema (frontale): {system_total_area_front_side_m2} m^2")
print(f"Efficienza del modulo: {module_efficiency*100:.1f}%")
print(f"Fattore di bifacialità: {bifaciality_factor:.2f}")
print(f"Periodo di simulazione: 1 anno ({len(times)} ore)")

print("\n--- Produzione Annuale Totale per Angolo di Tilt (kWh) ---")
display(results_df.round(2)) # Arrotonda per una migliore leggibilità

# Trova l'angolo di tilt che massimizza la produzione per la bifacciale
best_bifacial_tilt_row = results_df.loc[results_df['Bifacial_Annual_kWh'].idxmax()]
best_bifacial_tilt = best_bifacial_tilt_row['Tilt_Degrees']
max_bifacial_kwh = best_bifacial_tilt_row['Bifacial_Annual_kWh']

# Trova l'angolo di tilt che massimizza la produzione per la monofacciale
best_monofacial_tilt_row = results_df.loc[results_df['Monofacial_Annual_kWh'].idxmax()]
best_monofacial_tilt = best_monofacial_tilt_row['Tilt_Degrees']
max_monofacial_kwh = best_monofacial_tilt_row['Monofacial_Annual_kWh']

print(f"\n--- Angolo di Tilt Ottimale ---")
print(f"Per impianto BIFACCIALE: Tilt di {best_bifacial_tilt}° con una produzione annuale di {max_bifacial_kwh:.2f} kWh")
print(f"Per impianto MONOFACCIALE: Tilt di {best_monofacial_tilt}° con una produzione annuale di {max_monofacial_kwh:.2f} kWh")

# Calcolo del guadagno percentuale del tilt bifacciale rispetto a monofacciale al rispettivo ottimo
# E anche il guadagno della bifacciale rispetto alla monofacciale al tilt monofacciale ottimo
gain_at_bifacial_optimum = ((max_bifacial_kwh - results_df[results_df['Tilt_Degrees'] == best_bifacial_tilt]['Monofacial_Annual_kWh'].iloc[0]) / results_df[results_df['Tilt_Degrees'] == best_bifacial_tilt]['Monofacial_Annual_kWh'].iloc[0]) * 100
gain_at_monofacial_optimum = ((results_df[results_df['Tilt_Degrees'] == best_monofacial_tilt]['Bifacial_Annual_kWh'].iloc[0] - max_monofacial_kwh) / max_monofacial_kwh) * 100


print(f"Guadagno Bifacciale (al suo tilt ottimale) rispetto a Monofacciale (al suo stesso tilt): {gain_at_bifacial_optimum:.2f}%")
print(f"Guadagno Bifacciale (al tilt ottimale monofacciale) rispetto a Monofacciale (al suo tilt ottimale): {gain_at_monofacial_optimum:.2f}%")


# %%
# --- VISUALIZZAZIONE GRAFICA DEI RISULTATI ---

plt.figure(figsize=(14, 7))
plt.plot(results_df['Tilt_Degrees'], results_df['Bifacial_Annual_kWh'], marker='o', label='Bifacciale Annuale kWh')
plt.plot(results_df['Tilt_Degrees'], results_df['Monofacial_Annual_kWh'], marker='x', linestyle='--', label='Monofacciale Annuale kWh')

# Evidenzia i punti ottimali
plt.axvline(x=best_bifacial_tilt, color='green', linestyle=':', label=f'Best Bifacial Tilt: {best_bifacial_tilt}°')
plt.axvline(x=best_monofacial_tilt, color='red', linestyle=':', label=f'Best Monofacial Tilt: {best_monofacial_tilt}°')

plt.title('Produzione Annuale Totale vs. Angolo di Tilt')
plt.xlabel('Angolo di Tilt [Gradi]')
plt.ylabel('Produzione Annuale [kWh]')
plt.xticks(list(tilt_range)) # Assicura che ogni tick sia un grado del range
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()
plt.tight_layout()
plt.show()
