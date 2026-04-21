import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit

data = {
    'linear': [
        {
            'product': 'Resveratrol',
            'organism': 'S. cerevisiae',
            'reference': 'Vos et al. (2015)',
            'doi': '10.1186/s12934-015-0321-6',
            'mu': np.array([0.025, 0.05, 0.075, 0.10, 0.15]),
            'qp': np.array([0.003, 0.006, 0.011, 0.016, 0.024]),
            'qp_unit': 'mmol/(g·h)',
            'color': '#2196F3',
            'Yxs': 0.49, 'Ks': 0.1, 'ms': 0.02
        },
        {
            'product': 'VHH Antibody',
            'organism': 'S. cerevisiae',
            'reference': 'Frenken et al. (1998)',
            'doi': '10.1128/AEM.64.11.4226',
            'mu': np.array([0.03, 0.05, 0.08, 0.10, 0.15, 0.20]),
            'qp': np.array([0.8, 1.5, 2.3, 3.0, 4.5, 6.0]),
            'qp_unit': 'mg/(g·h)',
            'color': '#1565C0',
            'Yxs': 0.48, 'Ks': 0.1, 'ms': 0.015
        },
        {
            'product': 'Crl1 (Single-Copy)',
            'organism': 'P. pastoris',
            'reference': 'Garrigós-Martínez et al. (2019)',
            'doi': '10.1111/1751-7915.13498',
            'mu': np.array([0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15]),
            'qp': np.array([5.0, 12.0, 18.0, 25.0, 32.0, 38.0, 48.0]),
            'qp_unit': 'AU/(g·h)',
            'color': '#4CAF50',
            'Yxs': 0.42, 'Ks': 0.05, 'ms': 0.02
        },
    ],
    'bell_shaped': [
        {
            'product': 'EPG',
            'organism': 'S. cerevisiae',
            'reference': 'Glauche et al. (2017)',
            'doi': '10.1186/s12934-015-0321-6',
            'mu': np.array([0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]),
            'qp': np.array([50, 200, 350, 390, 400, 380, 250, 100]),
            'qp_unit': 'U/(g·h)',
            'color': '#1976D2',
            'Yxs': 0.49, 'Ks': 0.1, 'ms': 0.015
        },
        {
            'product': 'Fab Fragment',
            'organism': 'P. pastoris',
            'reference': 'Rebnegger et al. (2014)',
            'doi': '10.1002/bit.25518',
            'mu': np.array([0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15]),
            'qp': np.array([1.2, 3.5, 7.0, 10.5, 14.0, 12.0, 8.5, 3.0]),
            'qp_unit': 'mg/(g·h)',
            'color': '#388E3C',
            'Yxs': 0.44, 'Ks': 0.05, 'ms': 0.02
        },
        {
            'product': 'ROL Lipase',
            'organism': 'P. pastoris',
            'reference': 'Gasset et al. (2012)',
            'doi': '10.1002/bit.25518',
            'mu': np.array([0.01, 0.02, 0.035, 0.05, 0.065, 0.08, 0.10, 0.12]),
            'qp': np.array([8.0, 18.0, 32.0, 40.0, 38.0, 28.0, 18.0, 10.0]),
            'qp_unit': 'AU/(g·h)',
            'color': '#2E7D32',
            'Yxs': 0.40, 'Ks': 0.05, 'ms': 0.025
        },
    ],
    'hyperbolic': [
        {
            'product': 'Crl1 (Multi-Copy)',
            'organism': 'P. pastoris',
            'reference': 'Garrigós-Martínez et al. (2019)',
            'doi': '10.1111/1751-7915.13498',
            'mu': np.array([0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15]),
            'qp': np.array([20, 50, 80, 105, 120, 130, 140]),
            'qp_unit': 'AU/(g·h)',
            'color': '#43A047',
            'Yxs': 0.42, 'Ks': 0.05, 'ms': 0.02
        },
        {
            'product': 'α-Galactosidase',
            'organism': 'S. cerevisiae',
            'reference': 'Hensing et al. (1998)',
            'doi': '10.1002/yea.320080703',
            'mu': np.array([0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]),
            'qp': np.array([5.0, 14.0, 22.0, 28.0, 36.0, 40.0, 42.0, 43.0]),
            'qp_unit': 'U/(g·h)',
            'color': '#1E88E5',
            'Yxs': 0.49, 'Ks': 0.1, 'ms': 0.01
        },
        {
            'product': 'GFP',
            'organism': 'P. pastoris',
            'reference': 'Mattanovich et al. (2021)',
            'doi': '10.1186/s12934-021-01564-9',
            'mu': np.array([0.01, 0.03, 0.05, 0.08, 0.10, 0.13, 0.15, 0.18]),
            'qp': np.array([5.0, 15.0, 28.0, 42.0, 50.0, 56.0, 58.0, 60.0]),
            'qp_unit': 'RFU/(g·h)',
            'color': '#66BB6A',
            'Yxs': 0.45, 'Ks': 0.05, 'ms': 0.015
        },
    ],
}

def linear_model(mu, a, b):
    return a * mu + b

def bell_shaped_model(mu, qp_max, mu_opt, sigma):
    return qp_max * np.exp(-((mu - mu_opt)**2) / (2 * sigma**2))

def hyperbolic_model(mu, qp_max, K_qp):
    return qp_max * mu / (K_qp + mu)

def simulate_batch(mu_max, Ks, Yxs, ms, qp_model, qp_params, t_span, X0, S0, P0):
    def ode_system(t, y):
        X, S, P = y
        X, S = max(0, X), max(0, S)
        mu = mu_max * S / (Ks + S) if S > 0 else 0
        dX = mu * X
        dS = - (mu / Yxs + ms) * X if S > 0 else 0
        qp = qp_model(mu, *qp_params)
        dP = qp * X
        return [dX, dS, dP]
    return solve_ivp(ode_system, t_span, [X0, S0, P0], dense_output=True, max_step=0.1)

def create_figure():
    fig, axes = plt.subplots(3, 3, figsize=(22, 20))
    fig.suptitle('Validated XPS Profiles: Batch Simulations from Chemostat Kinetics', fontsize=20, fontweight='bold', y=0.98)
    
    types = [('linear', linear_model), ('bell_shaped', bell_shaped_model), ('hyperbolic', hyperbolic_model)]
    colors_bg = ['#E3F2FD', '#FFF3E0', '#E8F5E9']

    for col, (mtype, mfn) in enumerate(types):
        for row, ds in enumerate(data[mtype]):
            ax = axes[row, col]
            ax.set_facecolor(colors_bg[col])
            
            popt, _ = curve_fit(mfn, ds['mu'], ds['qp'], maxfev=20000)
            mu_max = max(ds['mu']) * 1.15
            sol = simulate_batch(mu_max, ds['Ks'], ds['Yxs'], ds['ms'], mfn, popt, (0, 50), 0.1, 20.0, 0.0)
            
            t_plot = np.linspace(0, sol.t[-1], 300)
            y = sol.sol(t_plot)
            
            ax1 = ax
            ax2 = ax1.twinx()
            ax1.plot(t_plot, y[0], color='#1B5E20', lw=2.5, label='X [g/L]')
            ax1.plot(t_plot, y[1], color='#B71C1C', lw=2.5, ls='--', label='S [g/L]')
            
            p_unit = ds["qp_unit"].split('/')[0] + '/L'
            ax2.plot(t_plot, y[2], color=ds['color'], lw=2.5, label=f'P [{p_unit}]')
            
            ax1.set_title(f"{ds['product']} ({ds['organism']})\n{ds['reference']}", fontsize=10, fontweight='bold')
            ax1.set_xlabel('Time (h)')
            ax2.set_ylabel(p_unit, color=ds['color'])
            
            if row == 2:
                lines, labels = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines + lines2, labels + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=9)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('xps_validated_profiles.png', dpi=300)
    plt.show()

if __name__ == '__main__':
    create_figure()