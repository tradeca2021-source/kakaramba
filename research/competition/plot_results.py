"""Optional standalone research figure; needs matplotlib, not required for backtests."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/fibonacci-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME','/tmp/fibonacci-font-cache')
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).resolve().parents[1]/'results/competition'
dev=json.loads((out/'development.json').read_text())
hold=json.loads((out/'holdout.json').read_text())
limits=json.loads((out/'limit_exploratory.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
names=['Original stop entry','Selected market entry']
for offset,phase,color in [(-.19,'Development','#4169a1'),(.19,'Unused holdout','#b14b4b')]:
 rows=[next(x for x in (dev['candidates'] if phase=='Development' else hold['results']) if x['rules']['name']==name) for name in ['baseline_v3','reclaim_market']]
 vals=[x['aggregate']['net'] if phase=='Development' else x['summary']['net'] for x in rows]
 bars=axes[0].bar([i+offset for i in range(2)],vals,width=.36,label=phase,color=color)
 axes[0].bar_label(bars,labels=[f'${v:,.0f}' for v in vals],padding=4,fontsize=9)
axes[0].set_xticks(range(2),names);axes[0].set_title('Primary test: candidate failed holdout')
axes[0].legend(frameon=False);axes[0].set_ylabel('Net USDT after modeled costs and funding')
rows=limits['results'];values=[r['aggregate']['net'] for r in rows]
bars=axes[1].bar(range(3),values,color=['#4169a1','#b14b4b','#b14b4b'])
axes[1].bar_label(bars,labels=[f'${v:,.0f}\n{r["aggregate"]["trades"]} trades' for v,r in zip(values,rows)],padding=4,fontsize=9)
axes[1].set_xticks(range(3),['Stop control','50% limit','Cost-bounded limit'])
axes[1].set_title('Exploratory follow-up: more trades lost more')
for ax in axes:
 ax.axhline(0,color='#555',linewidth=.8);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False);ax.margins(y=.25)
fig.suptitle('Fibonacci BOS research — no variant earned validated promotion',fontsize=14)
fig.text(.5,-.035,'Development and exploration totals sum separate period accounts; holdout uses a fresh $100,000 account.',ha='center',fontsize=9)
fig.savefig(out/'research_comparison.png',dpi=170,bbox_inches='tight')
fig.savefig(out/'research_comparison.svg',bbox_inches='tight')
