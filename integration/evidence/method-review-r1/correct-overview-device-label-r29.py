from pathlib import Path
import sys,hashlib,json
script=Path('FlagPrism/experiments/study/plot_porting_overview.py').resolve()
text=script.read_text();assert text.count("('enflame', 'GCU300')")==1
text=text.replace("('enflame', 'GCU300')","('enflame', 'ZIXIAOC200')")
data=Path('paper/figures/study-porting-overview-data.csv');before=hashlib.sha256(data.read_bytes()).hexdigest()
sys.path.insert(0,str(script.parent))
sys.argv=[str(script),'--cuda','FlagPrism/experiments/study/results/2026-10-13-goal-nvidia-r008/overview-independent-r008','--enflame','FlagPrism/experiments/study/results/2026-10-13-porting/enflame-overview','--cann','FlagPrism/experiments/study/results/2026-10-13-goal-cann-r009','--output','paper/figures']
exec(compile(text,str(script),'exec'),{'__name__':'__main__','__file__':str(script)})
after=hashlib.sha256(data.read_bytes()).hexdigest();assert before==after
Path('artifacts/method-run/paper/overview-label-correction-r29.json').write_text(json.dumps({'original_plot_script':str(script),'original_script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'edit':'Only legend GCU300 becomes actual physical ZIXIAOC200; original Study checkout untouched.','data_csv_before_sha256':before,'data_csv_after_sha256':after,'numeric_data_unchanged':True},indent=2)+'\n')
print('Corrected physical device label; numeric data CSV SHA unchanged',after)
