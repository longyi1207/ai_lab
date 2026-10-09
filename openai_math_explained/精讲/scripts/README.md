# 精讲 scripts

These scripts compute the numbers marked "脚本实算" in the 精讲 chapters. Each script prints its results to stdout, and the chapters copy those results into the text.

| Chapter | Script(s) | Extra deps |
|---|---|---|
| 02 π 的无理性指数 | `02_pi_a.py`, `02_pi_b.py`, `02_pi_c.py` | mpmath |
| 03 矩阵乘法指数 | `03_matmul.py` | sympy |
| 04 唯一博弈猜想 | `04_ugc.py` | numpy, scipy |
| 05 L = BPL | `05_bpl_toy.py`, `05_bpl_spec.py` | numpy |
| 06 平面着色数 | `06_coloring.py` | — |
| 07 Thompson 群 F | `07_thompson.py` | — (uses `fractions` for exact arithmetic) |
| 08 Navier–Stokes | `08_navier_stokes.py` | numpy |
| 09 Vlasov–Maxwell | `09_vlasov_maxwell.py` | numpy |
| 10 Mézard–Parisi | `10_mezard_parisi.py` | numpy, scipy, networkx |

Chapter 01 has no script here: its numbers were computed inline while drafting.

To run a script:

```bash
pip install numpy scipy sympy mpmath networkx
python3 03_matmul.py
```

Scripts with random sampling (Monte Carlo, random graphs) can give slightly different values from run to run, unless the script fixes a seed.
