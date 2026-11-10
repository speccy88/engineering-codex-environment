"""Plot the actual ngspice RC fixture and its analytic residual for the README.

First run: python3 tests/test_ngspice/acceptance.py artifacts/showcase/eda/simulation
Then run:  python3 docs/showcase/render-simulation.py
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'artifacts/showcase/eda/simulation/rc.csv'
TARGET = Path(__file__).with_name('simulation.png')
data = np.loadtxt(SOURCE, delimiter=',', skiprows=1)
t, supply, measured, expected, absolute_error = data.T
evidence = json.loads(SOURCE.with_name('results.json').read_text())
assert evidence['status'] == 'passed'
assert data.shape[0] > 100 and np.all(np.isfinite(data))
assert np.max(absolute_error) < .01

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                     'axes.labelcolor': '#334155', 'xtick.color': '#64748b',
                     'ytick.color': '#64748b', 'axes.edgecolor': '#cbd5e1',
                     'axes.spines.top': False, 'axes.spines.right': False})
fig = plt.figure(figsize=(12.8, 8), dpi=100, facecolor='white')
fig.text(.10, .93, 'RC transient simulation', color='#15283b', fontsize=24, weight='bold')
fig.text(.10, .885, 'R = 1 kΩ     C = 1 µF     Time constant = 1 ms', color='#64748b', fontsize=14)
ax = fig.add_axes([.10, .39, .85, .43])
ax.plot(t*1000, measured, color='#008d9d', lw=3, label='ngspice output')
ax.plot(t*1000, expected, color='#20364c', lw=1.5, ls=(0,(5,5)), label='Analytic reference')
ax.axhline(5, color='#cbd5e1', lw=1, ls=':')
ax.axvline(1, color='#94a3b8', lw=1, ls=':')
ax.scatter([1], [5*(1-np.exp(-1))], color='#008d9d', s=50, zorder=5)
ax.annotate('3.16 V at 1 ms', xy=(1,5*(1-np.exp(-1))), xytext=(1.55,2.2),
            color='#334155', fontsize=12,
            arrowprops={'arrowstyle':'-', 'color':'#64748b', 'lw':1})
ax.set(xlim=(0,5), ylim=(0,5.35), ylabel='Output voltage (V)')
ax.set_xticks(range(6));ax.tick_params(labelbottom=False)
ax.grid(axis='y', color='#e8edf3', lw=.7)
ax.legend(loc='lower right', frameon=False, fontsize=12)
residual = fig.add_axes([.10, .15, .85, .15], sharex=ax)
residual.fill_between(t*1000, absolute_error*1e6, color='#b6dce1', alpha=.65)
residual.plot(t*1000, absolute_error*1e6, color='#008d9d', lw=1.5)
residual.set(xlabel='Time (ms)', ylabel='Error (µV)', ylim=(0,16))
residual.set_yticks([0,5,10,15]);residual.grid(axis='y',color='#e8edf3',lw=.7)
fig.text(.10,.045,f'{len(t)} simulated samples  ·  Maximum absolute error {np.max(absolute_error)*1e6:.2f} µV',
         fontsize=11,color='#64748b')
fig.savefig(TARGET, dpi=100, facecolor='white')
plt.close(fig)
print(TARGET)
