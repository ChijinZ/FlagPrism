"""MetaX SDK allocation, exact-stream completion and pinned readback transport."""
import ctypes
import os
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from .timeline_nvidia_late_storage import plan_late_storage


def plan_metax_storage(plan, **kwargs):
    # This is the shared bounded physical ring codec, independent of target ops.
    result = plan_late_storage(plan, **kwargs)
    result['storage_version'] = 'metax-late-1'
    return result


def _owner_device(method):
    @wraps(method)
    def call(self,owner):
        with self.device_context(owner['device']):
            return method(self,owner)
    return call


class MetaxTimelineTransport:
    def __init__(self):
        import torch, triton
        if triton.runtime.driver.active.get_current_target().backend != 'maca':
            raise RuntimeError('MetaX timeline requires the actual MACA target')
        self.torch=torch
        self.runtime=ctypes.CDLL(str(Path(os.environ.get('MACA_PATH','/opt/maca'))/'lib/libmcruntime.so'))
        p=ctypes.c_void_p;u=ctypes.c_uint;z=ctypes.c_size_t;i=ctypes.c_int
        for name,args in {'mcGetDevice':[ctypes.POINTER(i)],'mcSetDevice':[i],'mcMalloc':[ctypes.POINTER(p),z],'mcFree':[p],
                          'mcMallocHost':[ctypes.POINTER(p),z,u],'mcFreeHost':[p],
                          'mcMemsetAsync':[p,i,z,p],
                          'mcEventCreateWithFlags':[ctypes.POINTER(p),u],
                          'mcEventRecord':[p,p],'mcEventQuery':[p],'mcEventDestroy':[p],
                          'mcMemcpyAsync':[p,p,z,i,p],'mcStreamSynchronize':[p]}.items():
            fn=getattr(self.runtime,name);fn.argtypes=args;fn.restype=i
        self.runtime.mcGetErrorName.argtypes=[i];self.runtime.mcGetErrorName.restype=ctypes.c_char_p

    def check(self,status,operation):
        if status:
            name=self.runtime.mcGetErrorName(status)
            raise RuntimeError('MetaX '+operation+' failed: '+str(status)+' '+str(name))

    @contextmanager
    def device_context(self,device):
        previous=ctypes.c_int()
        self.check(self.runtime.mcGetDevice(ctypes.byref(previous)),'mcGetDevice')
        if previous.value!=device:self.check(self.runtime.mcSetDevice(device),'mcSetDevice(owner)')
        try:yield
        finally:
            if previous.value!=device:self.check(self.runtime.mcSetDevice(previous.value),'mcSetDevice(restore)')

    def validate_target(self,*,device,stream):
        if self.torch.cuda.current_device()!=device:
            raise RuntimeError('MetaX launch device changed')
        if self.torch.cuda.is_current_stream_capturing():
            raise RuntimeError('MetaX automatic timeline currently requires eager launches')
        if type(stream)is not int:raise ValueError('Actual MetaX launch stream is required')

    def plan_storage(self,plan,**kwargs):
        return plan_metax_storage(plan,**kwargs)

    @_owner_device
    def allocate(self,owner):
        resource={'device':0,'host':0,'event':0}
        try:
            for key,api,args in [('event','mcEventCreateWithFlags',(0,)),
                                 ('device','mcMalloc',(owner['physical_bytes'],)),
                                 ('host','mcMallocHost',(owner['physical_bytes'],0))]:
                pointer=ctypes.c_void_p()
                self.check(getattr(self.runtime,api)(ctypes.byref(pointer),*args),api)
                resource[key]=pointer.value
            if resource['device']%owner['layout']['alignment']:
                raise RuntimeError('MetaX native allocation does not satisfy scratch alignment')
            return resource
        except BaseException:
            for key,api in [('event','mcEventDestroy'),('host','mcFreeHost'),('device','mcFree')]:
                if resource[key]:getattr(self.runtime,api)(resource[key])
            raise

    @_owner_device
    def initialize(self,owner):
        base=owner['resource']['device'];size=owner['layout']['raw_bytes']
        for address,value,length in ((base,0,size),(base+size,165,owner['guard_bytes'])):
            if length:self.check(self.runtime.mcMemsetAsync(address,value,length,owner['stream']),'mcMemsetAsync')

    def launch_buffer(self,owner):
        return owner['resource']['device']

    @_owner_device
    def record_completion(self,owner):
        self.check(self.runtime.mcEventRecord(owner['resource']['event'],owner['stream']),'mcEventRecord')

    @_owner_device
    def completion_ready(self,owner):
        status=self.runtime.mcEventQuery(owner['resource']['event'])
        if not status:return True
        if status==600:return False  # mcErrorNotReady from the installed MACA runtime headers
        self.check(status,'mcEventQuery')

    @_owner_device
    def read_raw(self,owner):
        from .timeline_runtime import TimelineReadback
        r=owner['resource']
        self.check(self.runtime.mcMemcpyAsync(r['host'],r['device'],owner['physical_bytes'],2,owner['stream']),'mcMemcpyAsync')
        self.check(self.runtime.mcStreamSynchronize(owner['stream']),'mcStreamSynchronize(readback stream)')
        result=ctypes.string_at(r['host'],owner['physical_bytes']);size=owner['layout']['raw_bytes']
        guard=result[size:]
        return TimelineReadback(result[:size],guard,() if guard==bytes([165])*owner['guard_bytes'] else ('allocation_guard_changed',))

    @_owner_device
    def release(self,owner):
        resource=owner['resource']
        for key,api in [('event','mcEventDestroy'),('host','mcFreeHost'),('device','mcFree')]:
            if resource[key]:
                self.check(getattr(self.runtime,api)(resource[key]),api)
                resource[key]=0
        owner['resource']=None
