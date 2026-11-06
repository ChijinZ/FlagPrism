"""Exercise actual patched Python callback and allocation admission without GPU."""
import argparse, ast
from pathlib import Path
from types import SimpleNamespace as NS

def method(path,cls,name,env):
    tree=ast.parse(path.read_text());node=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name==cls for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name)
    node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env);return env[name]

def check(root):
    events=[]
    class Allocator:
        reject=False
        def validate_launch(self,**kw):
            events.append(('validate',kw))
            if self.reject:raise ValueError('admission rejected')
        def __call__(self,size,alignment,stream):events.append(('allocate',size));return 'buffer'
    allocator=Allocator();allocation=NS(_profile_allocator=NS(get=lambda:allocator),_allocator=NS(get=lambda:None))
    launch=method(root/'driver.py','MacaLauncher','__call__',{'_allocation':allocation})
    owner=NS(num_ctas=1,metadata=NS(debug_enabled=False),global_scratch_size=0,global_scratch_align=1,profile_scratch_size=128,profile_scratch_align=8,launch=lambda *a:events.append(('launch',a)))
    launch(owner,2,3,1,19,101)
    assert [e[0] for e in events]==['validate','allocate','launch']
    assert events[0][1]==dict(function=101,grid=(2,3,1),scratch_size=128,alignment=8,num_ctas=1,stream=19)
    assert events[1][1]==768
    events.clear();allocator.reject=True
    try:launch(owner,2,3,1,19,101)
    except ValueError:pass
    else:raise AssertionError('Rejected launch continued')
    assert [e[0] for e in events]==['validate']
    calls=[]
    def transform(text,metadata):calls.append(text);metadata['profile_scratch_size']=128;return text+' transformed'
    backend=NS(instrumentation=NS(transform_optimized_llvm=transform))
    env={'MACABackend':backend,'knobs':NS(metax=NS(mlir_opt_path='opt',mlir_translate_path='translate')),'metax':NS(mlir_opt=lambda s,p:s,translate_mlir_to_llir=lambda s,p:'ordinary'),'maca_get_kernel_name':lambda s:'user_kernel'}
    convert=method(root/'compiler.py','MACABackend','make_llir',env);metadata={}
    assert convert('input',metadata,NS(extern_libs=[]),0)=='ordinary transformed'
    assert calls==['ordinary'] and metadata['profile_scratch_size']==128 and metadata['name']=='user_kernel'
    backend.instrumentation=None
    assert convert('input',{},NS(extern_libs=[]),0)=='ordinary'
    backend.instrumentation=NS(transform_optimized_llvm=lambda text,metadata:None)
    try:convert('input',{},NS(extern_libs=[]),0)
    except RuntimeError:pass
    else:raise AssertionError('Invalid callback output accepted')
    tree=ast.parse((root/'jit.py').read_text())
    statement=next(n for n in ast.walk(tree) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='setdefault' and n.value.args and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='instrumentation_mode')
    code=compile(ast.Module(body=[statement],type_ignores=[]),'jit.py','exec')
    explicit={'instrumentation_mode':'capture-binary-key'}
    exec(code,{'kwargs':explicit,'knobs':NS(compilation=NS(instrumentation_mode=''))})
    assert explicit['instrumentation_mode']=='capture-binary-key'
    ordinary={};exec(code,{'kwargs':ordinary,'knobs':NS(compilation=NS(instrumentation_mode='default-mode'))})
    assert ordinary['instrumentation_mode']=='default-mode'
    print('7 checks passed: admission geometry/order/rejection, callback metadata, ordinary path, invalid transform, explicit cache key and default cache key')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);check(p.parse_args().source)
