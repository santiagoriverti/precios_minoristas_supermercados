import pickle, sys, numpy as np, pandas as pd
a = pickle.load(open(sys.argv[1],'rb')); b = pickle.load(open(sys.argv[2],'rb'))
def srt(d): return d.sort_values(list(d.columns)).reset_index(drop=True)
ok = True
def chk(name, x, y):
    global ok
    try:
        pd.testing.assert_frame_equal(x, y, check_exact=False, rtol=1e-12); print('  IDENTICO', name, x.shape)
    except AssertionError as e:
        ok = False; print('  DIFIERE ', name, str(e)[:300])
chk('datos_sem (ordenado)', srt(a['datos_sem']), srt(b['datos_sem']))
chk('nac_item', a['nac_item'].reset_index(drop=True), b['nac_item'].reset_index(drop=True))
chk('nac_wide', a['nac_wide'], b['nac_wide'])
chk('N_SUC_ITEM_SEMANA', a['nsuc'], b['nsuc'])
chk('costo_suc (mismo orden de filas)', a['costo_suc'], b['costo_suc'])
print('pico RAM: vieja %.2f GB -> nueva %.2f GB' % (a['peak']/2**30, b['peak']/2**30))
print('RESULTADO:', 'IDENTICO' if ok else 'DIFIERE')
