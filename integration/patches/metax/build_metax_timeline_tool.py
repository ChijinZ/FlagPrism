"""Build the MetaX LLVM recorder with the shared bounded build driver."""
from pathlib import Path
import runpy,sys
root=Path(__file__).resolve().parents[3]
builder=root/'integration/patches/nvidia/build_late_timeline_tool.py'
sys.argv=[str(builder),'--source',str(root/'Profiler/Dialect/tools/metax-timeline/metax-timeline.cpp'),'--executable-name','metax-timeline',*sys.argv[1:]]
runpy.run_path(str(builder),run_name='__main__')
