import json, os, sys, time, matplotlib; matplotlib.use('Agg')
REPO=r'C:/Users/sriverti/Desktop/INECO/Repositorios/precios_minoristas_supermercados'
cells=[''.join(c['source']) for c in json.load(open(REPO+'/notebooks/10_canasta_reponderada_ipc.ipynb',encoding='utf-8'))['cells'] if c['cell_type']=='code']
g={}; exec(cells[0],g)
out=sys.argv[3] if len(sys.argv)>3 else os.path.dirname(os.path.abspath(__file__))+'/out_real'
g.update(CANASTA_EXCEL=sys.argv[1], SEPA_DIR=sys.argv[2], OUTPUT_DIR=out)
t=time.time()
for i,c in enumerate(cells[1:],1):
    exec(c,g); print(f'--- celda {i} ok ({time.time()-t:.0f}s)', flush=True)
