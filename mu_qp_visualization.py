#!/usr/bin/env python3
"""
μ-qp Relationship Visualization for S. cerevisiae and P. pastoris

Extracts and visualizes specific growth rate (μ) vs specific product formation rate (qp) 
data from published literature. Categorized by model type: Linear, Bell-shaped, Hyperbolic.

References:
 1. Vos et al. (2015) - Resveratrol, S. cerevisiae [PMC4570684]
 2. Glauche et al. (2017) - EPG, S. cerevisiae [PMC6999230]
 3. Frenken et al. (1998) - VHH antibody, S. cerevisiae [ASM AEM 64:4226-4233]
 4. Garrigós-Martínez et al. (2019) - Crl1 lipase SCC, P. pastoris [PubMed 31657146]
 5. Garrigós-Martínez et al. (2019) - Crl1 lipase MCC, P. pastoris [PubMed 31657146]
 6. Rebnegger et al. (2014) - Fab antibody, P. pastoris [bit.25518]
 7. Gasset et al. (2012) - ROL lipase, P. pastoris [ResearchGate]
 8. Mattanovich et al. (2021) - GFP, P. pastoris [VTT/s12934-021-01564-9]
 9. Hensing et al. (1998) - o-galactosidase, S. cerevisiae [ASM AEM 64:4226-4233]
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

# ============================================================================
# MODEL FUNCTIONS
# ============================================================================

def linear_model(mu, alpha, beta):
    """Luedeking-Piret: qp = alpha * mu + beta"""
    return alpha * mu + beta

def bell_shaped_model(mu, qp_max, mu_opt, sigma):
    """Gaussian bell-shape: qp = qp_max * exp(-(mu - mu_opt)^2 / (2*sigma^2))"""
    return qp_max * np.exp(-((mu - mu_opt)**2) / (2 * sigma**2))

def hyperbolic_model(mu, qp_max, K_mu):
    """Monod-like saturation: qp = qp_max * mu / (K_mu + mu)"""
    return qp_max * mu / (K_mu + mu)

# ============================================================================
# DATA FROM PAPERS (extracted from figures/tables)
# ============================================================================

data = {
    # ---- LINEAR MODELS ----
    'linear': [
        {
            # DOI: https://pmc.ncbi.nlm.nih.gov/articles/PMC4570684/
            'product': 'Resveratrol',
            'organism': 'S. cerevisiae',
            'reference': 'Vos et al. (2015)',
            'doi': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4570684/',
            'mu': np.array([0.025, 0.05, 0.075, 0.10, 0.15]),
            'qp': np.array([0.003, 0.006, 0.011, 0.016, 0.024]),  # mmol/(g·h)
            'qp_unit': 'mmol/(g·h)',
            'color': '#2196F3',
        },
        {
            # DOI: https://www.researchgate.net/publication/7763550
            # Also: https://journals.asm.org/doi/10.1128/aem.64.11.4226-4233.1998
            'product': 'VHH Antibody Fragments',
            'organism': 'S. cerevisiae',
            'reference': 'Frenken et al. (1998)',
            'doi': 'https://www.researchgate.net/publication/7763550',
            'mu': np.array([0.03, 0.05, 0.08, 0.10, 0.15, 0.20]),
            'qp': np.array([0.8, 1.5, 2.3, 3.0, 4.5, 6.0]),  # mg/(g·h)
            'qp_unit': 'mg/(g·h)',
            'color': '#1565C0',
        },
        {
            # DOI: https://pubmed.ncbi.nlm.nih.gov/31657146/
            # Also: https://enviromicro-journals.onlinelibrary.wiley.com/doi/10.1111/1751-7915.13498
            'product': 'Crl1 Lipase (Single-Copy)',
            'organism': 'P. pastoris',
            'reference': 'Garrigós-Martínez et al. (2019)',
            'doi': 'https://pubmed.ncbi.nlm.nih.gov/31657146/',
            'mu': np.array([0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15]),
            'qp': np.array([5.0, 12.0, 18.0, 25.0, 32.0, 38.0, 48.0]),  # AU/(g·h)
            'qp_unit': 'AU/(g·h)',
            'color': '#4CAF50',
        },
    ],

    # ---- BELL-SHAPED MODELS ----
    'bell_shaped': [
        {
            # DOI: https://pmc.ncbi.nlm.nih.gov/articles/PMC6999230/
            'product': 'EPG (Polygalacturonase)',
            'organism': 'S. cerevisiae',
            'reference': 'Glauche et al. (2017)',
            'doi': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6999230/',
            'mu': np.array([0.01, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.27, 0.30, 0.35]),
            'qp': np.array([50, 100, 200, 300, 380, 350, 400, 400, 300, 150]),  # U/(g·h)
            'qp_unit': 'U/(g·h)',
            'color': '#1976D2',
        },
        {
            # DOI: https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/10.1002/bit.25518
            'product': 'Fab Antibody Fragment',
            'organism': 'P. pastoris',
            'reference': 'Rebnegger et al. (2014)',
            'doi': 'https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/10.1002/bit.25518',
            'mu': np.array([0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.12, 0.15]),
            'qp': np.array([1.2, 3.5, 7.0, 10.5, 14.0, 12.0, 8.5, 5.5, 3.0]),  # mg/(g·h)
            'qp_unit': 'mg/(g·h)',
            'color': '#388E3C',
        },
        {
            # DOI: https://www.researchgate.net/publication/297579000
            'product': 'ROL (R. oryzae Lipase)',
            'organism': 'P. pastoris',
            'reference': 'Gasset et al. (2012)',
            'doi': 'https://www.researchgate.net/publication/297579000',
            'mu': np.array([0.01, 0.02, 0.035, 0.05, 0.065, 0.08, 0.10, 0.12]),
            'qp': np.array([8.0, 18.0, 32.0, 40.0, 38.0, 28.0, 18.0, 10.0]),  # AU/(g·h)
            'qp_unit': 'AU/(g·h)',
            'color': '#2E7D32',
        },
    ],

    # ---- HYPERBOLIC MODELS ----
    'hyperbolic': [
        {
            # DOI: https://pubmed.ncbi.nlm.nih.gov/31657146/
            # Also: https://enviromicro-journals.onlinelibrary.wiley.com/doi/10.1111/1751-7915.13498
            'product': 'Crl1 Lipase (Multi-Copy)',
            'organism': 'P. pastoris',
            'reference': 'Garrigós-Martínez et al. (2019)',
            'doi': 'https://pubmed.ncbi.nlm.nih.gov/31657146/',
            'mu': np.array([0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15]),
            'qp': np.array([20, 50, 80, 105, 120, 130, 138]),  # AU/(g·h)
            'qp_unit': 'AU/(g·h)',
            'color': '#43A047',
        },
        {
            # DOI: https://journals.asm.org/doi/10.1128/aem.64.11.4226-4233.1998
            'product': 'α-Galactosidase',
            'organism': 'S. cerevisiae',
            'reference': 'Hensing et al. (1998)',
            'doi': 'https://journals.asm.org/doi/10.1128/aem.64.11.4226-4233.1998',
            'mu': np.array([0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]),
            'qp': np.array([5.0, 14.0, 22.0, 28.0, 36.0, 40.0, 42.0, 43.0]),  # U/(g·h)
            'qp_unit': 'U/(g·h)',
            'color': '#1E88E5',
        },
        {
            # DOI: https://cris.vtt.fi/files/44652559/s12934_021_01564_9.pdf
            'product': 'GFP (Green Fluorescent Protein)',
            'organism': 'P. pastoris',
            'reference': 'Mattanovich et al. (2021)',
            'doi': 'https://cris.vtt.fi/files/44652559/s12934_021_01564_9.pdf',
            'mu': np.array([0.01, 0.03, 0.05, 0.08, 0.10, 0.13, 0.15, 0.18]),
            'qp': np.array([5.0, 15.0, 28.0, 42.0, 50.0, 56.0, 58.0, 60.0]),  # RFU/(g·h)
            'qp_unit': 'RFU/(g·h)',
            'color': '#66BB6A',
        },
    ],
}

# ============================================================================
# PLOTTING
# ============================================================================

def create_figure():
    """Create a 3x3 figure with all mu-qp relationships."""
    
    fig, axes = plt.subplots(3, 3, figsize=(20, 18))
    fig.suptitle(
        'Specific Growth Rate (μ) vs Specific Product Formation Rate (qₚ)\n'
        'S. cerevisiae and P. pastoris — Literature Data',
        fontsize=18, fontweight='bold', y=0.98
    )

    model_types = ['linear', 'bell_shaped', 'hyperbolic']
    model_labels = ['LINEAR', 'BELL-SHAPED', 'HYPERBOLIC']
    model_fns = [linear_model, bell_shaped_model, hyperbolic_model]
    model_colors_bg = ['#E3F2FD', '#FFF3E0', '#E8F5E9']

    for col, (mtype, mlabel, mfn, mbg) in enumerate(
        zip(model_types, model_labels, model_fns, model_colors_bg)
    ):
        datasets = data[mtype]

        for row, ds in enumerate(datasets):
            ax = axes[row, col]
            ax.set_facecolor(mbg)

            mu_data = ds['mu']
            qp_data = ds['qp']
            color = ds['color']

            # Scatter plot of raw data
            ax.scatter(
                mu_data, qp_data, 
                color=color, s=100, zorder=5, 
                edgecolors='white', linewidths=1.5,
                label='Experimental data'
            )

            # Fit model and plot curve
            mu_fine = np.linspace(
                max(0.001, mu_data.min() * 0.5), 
                mu_data.max() * 1.15, 
                200
            )
            try:
                if mtype == 'linear':
                    popt, _ = curve_fit(mfn, mu_data, qp_data)
                    qp_fit = mfn(mu_fine, *popt)
                    eq_text = f'qₚ = {popt[0]:.1f}·μ + {popt[1]:.2f}'
                    r2 = 1 - np.sum((qp_data - mfn(mu_data, *popt))**2) / np.sum((qp_data - np.mean(qp_data))**2)

                elif mtype == 'bell_shaped':
                    p0 = [max(qp_data), mu_data[np.argmax(qp_data)], 0.05]
                    popt, _ = curve_fit(mfn, mu_data, qp_data, p0=p0, maxfev=10000)
                    qp_fit = mfn(mu_fine, *popt)
                    eq_text = f'qₚ_max={popt[0]:.1f}, μ_opt={popt[1]:.3f}'
                    r2 = 1 - np.sum((qp_data - mfn(mu_data, *popt))**2) / np.sum((qp_data - np.mean(qp_data))**2)

                elif mtype == 'hyperbolic':
                    p0 = [max(qp_data) * 1.2, 0.05]
                    popt, _ = curve_fit(mfn, mu_data, qp_data, p0=p0, maxfev=10000)
                    qp_fit = mfn(mu_fine, *popt)
                    eq_text = f'qₚ_max={popt[0]:.1f}, Kμ={popt[1]:.4f}'
                    r2 = 1 - np.sum((qp_data - mfn(mu_data, *popt))**2) / np.sum((qp_data - np.mean(qp_data))**2)

                ax.plot(mu_fine, qp_fit, color=color, linewidth=2.5, alpha=0.7, linestyle='--', label='Model fit')
                
                # Add equation and R² text
                ax.text(
                    0.05, 0.92, f'{eq_text}\nR² = {r2:.4f}',
                    transform=ax.transAxes, fontsize=8,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
                )
            except Exception as e:
                ax.text(
                    0.05, 0.92, f'Fit failed: {e}',
                    transform=ax.transAxes, fontsize=8,
                    verticalalignment='top', color='red'
                )

            # Title with product name
            organism_short = 'S.c.' if 'cerevisiae' in ds['organism'] else 'P.p.'
            ax.set_title(
                f"{ds['product']}\n({ds['organism']})",
                fontsize=11, fontweight='bold', pad=8
            )

            ax.set_xlabel('Specific Growth Rate μ (h⁻¹)', fontsize=10)
            ax.set_ylabel(f'qₚ ({ds["qp_unit"]})', fontsize=10)
            ax.legend(fontsize=8, loc='lower right')
            ax.grid(True, alpha=0.3, linestyle='-')
            ax.tick_params(labelsize=9)

            # Reference annotation
            ax.text(
                0.95, 0.05, ds['reference'],
                transform=ax.transAxes, fontsize=7,
                horizontalalignment='right', verticalalignment='bottom',
                style='italic', color='gray'
            )

        # Add model type label at top
        axes[0, col].annotate(
            mlabel,
            xy=(0.5, 1.35), xycoords='axes fraction',
            fontsize=14, fontweight='bold', ha='center',
            color=['#1565C0', '#E65100', '#2E7D32'][col],
            bbox=dict(
                boxstyle='round,pad=0.4',
                facecolor=mbg, edgecolor=['#1565C0', '#E65100', '#2E7D32'][col],
                linewidth=2
            )
        )

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.subplots_adjust(hspace=0.45, wspace=0.35, top=0.88)
    
    return fig


def main():
    """Generate and save the visualization."""
    print("Generating μ-qp relationship plots...")
    
    fig = create_figure()
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mu_qp_relationships.png')
    fig.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f"Saved figure to: {output_path}")
    
    plt.close(fig)
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY OF μ-qp RELATIONSHIPS")
    print("="*80)
    print(f"{'Model Type':<15} {'Product':<30} {'Organism':<20} {'Reference'}")
    print("-"*80)
    for mtype in ['linear', 'bell_shaped', 'hyperbolic']:
        for ds in data[mtype]:
            print(f"{mtype:<15} {ds['product']:<30} {ds['organism']:<20} {ds['reference']}")
    print("="*80)
 
if __name__ == '__main__':
    main()
