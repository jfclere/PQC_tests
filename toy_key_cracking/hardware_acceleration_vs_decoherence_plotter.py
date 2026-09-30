import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# Presentation Style & Dimensions (Optimized for 16:9 Slides)
# =====================================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'Liberation Sans']

fig, ax = plt.subplots(figsize=(12, 6.75), dpi=300)

# Theoretical physical error model: F(g) = (1 - epsilon)^g
# Based on IBM Heron (ibm_fez) average 2-qubit gate error rate epsilon ~ 0.3% (0.003)
epsilon = 0.003
gates = np.linspace(0, 3200, 1000)
fidelity = ((1 - epsilon) ** gates) * 100

# Benchmark Data Points from Empirical Experiments
benchmarks = [
    {"name": "N = 15 (7Q)", "gates": 50, "fidelity": 85.0, "color": "#16a34a", "note": "Clean Phase Signal"},
    {"name": "N = 21 (11Q)", "gates": 120, "fidelity": 68.0, "color": "#2563eb", "note": "Clear Period Peaks (r=6)"},
    {"name": "N = 35 (12Q)", "gates": 400, "fidelity": 30.0, "color": "#ea580c", "note": "Physical NISQ Ceiling"},
    {"name": "N = 55 (14Q)", "gates": 2840, "fidelity": 0.02, "color": "#dc2626", "note": "Total Decoherence (White Noise)"}
]

# Background regions
ax.axvspan(1000, 3300, color='#fee2e2', alpha=0.35, label='Decoherence Zone (Unusable for Period Finding)')
ax.axhline(y=1.0, color='#94a3b8', linestyle=':', linewidth=1.5, label='Classical Readout Noise Floor (~1%)')

# Plot the theoretical decay line
ax.plot(gates, fidelity, color='#1e293b', linewidth=2.8, linestyle='-', label=r'Fidelity Decay: $F = (1 - \epsilon)^{N_{\mathrm{gates}}}$ ($\epsilon=0.3\%$)')

# Plot experimental points
for pt in benchmarks:
    ax.scatter(pt["gates"], pt["fidelity"], color=pt["color"], s=130, zorder=5, edgecolors='#0f172a', linewidth=1.8)

# Point Annotations & Callouts
# N = 15
ax.annotate(f"🟢 {benchmarks[0]['name']}\n{benchmarks[0]['note']}\n({benchmarks[0]['gates']} physical gates)",
            xy=(benchmarks[0]['gates'], benchmarks[0]['fidelity']),
            xytext=(benchmarks[0]['gates'] + 100, benchmarks[0]['fidelity'] + 5),
            fontsize=11, fontweight='bold', color='#15803d',
            arrowprops=dict(arrowstyle="->", color='#16a34a', lw=1.5))

# N = 21
ax.annotate(f"🔵 {benchmarks[1]['name']}\n{benchmarks[1]['note']}\n(~{benchmarks[1]['gates']} physical gates)",
            xy=(benchmarks[1]['gates'], benchmarks[1]['fidelity']),
            xytext=(benchmarks[1]['gates'] + 120, benchmarks[1]['fidelity'] + 6),
            fontsize=11, fontweight='bold', color='#1d4ed8',
            arrowprops=dict(arrowstyle="->", color='#2563eb', lw=1.5))

# N = 35 (NISQ Limit Callout)
ax.annotate(f"🟠 {benchmarks[2]['name']} — NISQ Ceiling\n{benchmarks[2]['note']}\n(~{benchmarks[2]['gates']} physical gates)",
            xy=(benchmarks[2]['gates'], benchmarks[2]['fidelity']),
            xytext=(benchmarks[2]['gates'] + 150, benchmarks[2]['fidelity'] + 16),
            fontsize=11, fontweight='bold', color='#c2410c',
            bbox=dict(boxstyle="round,pad=0.4", fc="#ffedd5", ec="#ea580c", lw=1.5),
            arrowprops=dict(arrowstyle="->", color='#ea580c', lw=1.5))

# N = 55 (Noise Wall Callout)
ax.annotate(f"🔴 {benchmarks[3]['name']}\n{benchmarks[3]['note']}\n({benchmarks[3]['gates']} physical gates, F < 0.02%)",
            xy=(benchmarks[3]['gates'], benchmarks[3]['fidelity']),
            xytext=(benchmarks[3]['gates'] - 950, benchmarks[3]['fidelity'] + 18),
            fontsize=11, fontweight='bold', color='#b91c1c',
            bbox=dict(boxstyle="round,pad=0.4", fc="#fee2e2", ec="#dc2626", lw=1.5),
            arrowprops=dict(arrowstyle="->", color='#dc2626', lw=1.5))

# Axes and Grid Formatting
ax.set_title("Hardware Acceleration vs. Decoherence in Shor's Algorithm\nEmpirical Scaling Limits on IBM Quantum Hardware (Heron Architecture)",
             fontsize=16, fontweight='bold', color='#0f172a', pad=18)
ax.set_xlabel("Physical 2-Qubit Gate Count (Transpiled ECR / CZ Operations)", fontsize=13, fontweight='bold', color='#1e293b', labelpad=10)
ax.set_ylabel("Output State Fidelity (%)", fontsize=13, fontweight='bold', color='#1e293b', labelpad=10)

ax.set_xlim(-80, 3200)
ax.set_ylim(-4, 105)

ax.grid(True, linestyle='--', alpha=0.5, color='#cbd5e1')
ax.set_axisbelow(True)

# Clean legend
ax.legend(loc='upper right', frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1', fontsize=10)

# Fine-tune tick styles
ax.tick_params(axis='both', which='major', labelsize=11)
for spine in ax.spines.values():
    spine.set_color('#94a3b8')

plt.tight_layout()

# Save publication-grade PNG
output_filename = "hardware_acceleration_vs_decoherence.png"
plt.savefig(output_filename, dpi=300, bbox_inches='tight')
print(f"Graph successfully generated and saved to '{output_filename}' (300 DPI).")