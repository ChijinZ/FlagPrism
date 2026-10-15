"""Patch the pinned independent FlagTree launcher; execute inside Docker.

This is pending code, not an exported/validated runtime patch. The original
driver is the public immutable 0364ed4 source. No SDK binary is changed.
"""
from pathlib import Path
import hashlib
import sys

CPP_COMMON = r'''
#include <memory>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/syscall.h>

static PyObject* flagprism_receipt_capsule(PyObject* metadata) {
  if (!metadata || metadata == Py_None) return nullptr;
  if (PyDict_Check(metadata)) {
    PyObject* value = PyDict_GetItemString(metadata, "_flagprism_cann_launch_receipt_v1");
    if (value) { Py_INCREF(value); return value; }
  }
  PyObject* value = PyObject_GetAttrString(metadata, "_flagprism_cann_launch_receipt_v1");
  if (!value && PyErr_ExceptionMatches(PyExc_AttributeError)) PyErr_Clear();
  return value;
}
'''

CPP_SUPPORTED = r'''
using FlagPrismReceiptSinkHandle = std::shared_ptr<proton::CannLaunchReceiptSinkV1>;

static FlagPrismReceiptSinkHandle flagprism_get_receipt_sink(PyObject* metadata) {
  PyObject* capsule = flagprism_receipt_capsule(metadata);
  if (!capsule) return {};
  if (capsule == Py_None) { Py_DECREF(capsule); return {}; }
  if (!PyCapsule_IsValid(capsule, proton::kCannLaunchReceiptCapsuleName)) {
    Py_DECREF(capsule);
    PyErr_SetString(PyExc_TypeError, "CANN launch receipt capsule name/version mismatch");
    return {};
  }
  auto* sink = static_cast<proton::CannLaunchReceiptSinkV1*>(
      PyCapsule_GetPointer(capsule, proton::kCannLaunchReceiptCapsuleName));
  if (!sink || sink->abiVersion != proton::kCannLaunchReceiptAbiVersion ||
      sink->structSize != sizeof(proton::CannLaunchReceiptSinkV1) ||
      !sink->context || !sink->retain || !sink->release || !sink->publish || !sink->cancel) {
    Py_DECREF(capsule);
    PyErr_SetString(PyExc_ValueError, "CANN launch receipt capsule ABI is incomplete");
    return {};
  }
  sink->retain(sink->context);
  Py_DECREF(capsule);
  try {
    return FlagPrismReceiptSinkHandle(sink, [](auto* retained) {
      retained->release(retained->context);
    });
  } catch (const std::bad_alloc&) {
    // shared_ptr's constructor invokes the deleter on allocation failure.
    PyErr_NoMemory();
    return {};
  }
}

static void flagprism_publish_receipt(const FlagPrismReceiptSinkHandle& sink,
                                     rtStream_t stream, rtError_t launchStatus,
                                     uint32_t actualBlockNum) {
  if (!sink) return;
  proton::CannLaunchWorkerRecordV1 record;
  record.processId = static_cast<uint64_t>(getpid());
  record.threadId = static_cast<uint64_t>(syscall(SYS_gettid));
  record.streamHandle = reinterpret_cast<uint64_t>(stream);
  record.launchStatus = static_cast<int32_t>(launchStatus);
  if (launchStatus == RT_ERROR_NONE && actualBlockNum) {
    // Read the last task before any other SDK call, on this actual worker.
    using TaskQuery = aclError (*)(uint32_t*);
    using StreamQuery = aclError (*)(aclrtStream, int32_t*);
    using DeviceQuery = aclError (*)(int32_t*);
    static auto taskQuery = reinterpret_cast<TaskQuery>(
        dlsym(RTLD_DEFAULT, "aclrtGetThreadLastTaskId"));
    static auto streamQuery = reinterpret_cast<StreamQuery>(
        dlsym(RTLD_DEFAULT, "aclrtStreamGetId"));
    static auto deviceQuery = reinterpret_cast<DeviceQuery>(
        dlsym(RTLD_DEFAULT, "aclrtGetDevice"));
    record.taskQueryStatus = taskQuery ? taskQuery(&record.taskId) : -2;
    record.streamQueryStatus = streamQuery ? streamQuery(stream, &record.streamId) : -2;
    record.deviceQueryStatus = deviceQuery ? deviceQuery(&record.deviceId) : -2;
  }
  sink->publish(sink->context, &record);
}
'''

CPP_LEGACY = r'''
using FlagPrismReceiptSinkHandle = std::shared_ptr<void>;
static FlagPrismReceiptSinkHandle flagprism_get_receipt_sink(PyObject* metadata) {
  PyObject* capsule = flagprism_receipt_capsule(metadata);
  if (!capsule) return {};
  bool present = capsule != Py_None;
  Py_DECREF(capsule);
  if (present) PyErr_SetString(PyExc_RuntimeError,
      "CANN receipt capsule supplied but its ABI provider is unavailable; rebuild the profiler/launcher");
  return {};
}
static void flagprism_publish_receipt(const FlagPrismReceiptSinkHandle&,
                                     rtStream_t, rtError_t, uint32_t) {}
'''


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(
            'pinned launcher structural anchor missing or ambiguous: ' +
            old[:100])
    return text.replace(old, new, 1)


def patch_driver(path):
    text = path.read_text()
    if 'def _flagprism_cann_receipt_cpp(' in text:
        raise RuntimeError(
            'launcher receipt patch already present; inspect/export instead of reapplying'
        )
    helper = '\n\ndef _flagprism_cann_receipt_cpp(abi):\n'
    helper += '    """Embed exact provider bytes; wrapper_src cache identity includes this ABI."""\n'
    helper += f'    common = {CPP_COMMON!r}\n'
    helper += f'    supported = {CPP_SUPPORTED!r}\n'
    helper += f'    legacy = {CPP_LEGACY!r}\n'
    helper += '    return common + (abi + supported if abi else legacy)\n\n'
    text = replace_once(text, 'class NPUUtils(object):',
                        helper + 'class NPUUtils(object):')
    text = replace_once(
        text,
        '    debug_abi = _DebuggerHiddenArgABI.from_metadata(metadata)  # FlagPrism',
        '    debug_abi = _DebuggerHiddenArgABI.from_metadata(metadata)  # FlagPrism\n'
        '    receipt_cpp = _flagprism_cann_receipt_cpp(_flagprism.get_cann_launch_receipt_abi())'
    )
    text = replace_once(text, '{cpp_msprof_extern}\n',
                        '{cpp_msprof_extern}\n{receipt_cpp}\n')
    text = replace_once(
        text,
        'int gridX, int gridY, int gridZ, std::vector<std::vector<int64_t>> &tensorShapes',
        'int gridX, int gridY, int gridZ, FlagPrismReceiptSinkHandle receiptSink, std::vector<std::vector<int64_t>> &tensorShapes'
    )
    text = replace_once(
        text, '    {cpp_kernel_launch}\n',
        '    {cpp_kernel_launch}\n    flagprism_publish_receipt(receiptSink, stream, ret, blockNum);\n'
    )
    text = replace_once(
        text, '  // get kernel_name\n',
        '  auto receiptSink = flagprism_get_receipt_sink(launch_metadata);\n'
        '  if (PyErr_Occurred()) return NULL;\n\n  // get kernel_name\n')
    text = replace_once(
        text,
        '_launch(kernelName, function, stream, gridX, gridY, gridZ, tensorShapes, tensorKinds',
        '_launch(kernelName, function, stream, gridX, gridY, gridZ, receiptSink, tensorShapes, tensorKinds'
    )
    path.write_text(text)


def patch_shim(path):
    text = path.read_text()
    if 'def get_cann_launch_receipt_abi(' in text:
        return
    text += '''\n\ndef get_cann_launch_receipt_abi() -> str:
    """Optional authoritative C ABI for generated SDK launch-worker receipts."""
    values = []
    for callback in _registered_callbacks("get_cann_launch_receipt_abi"):
        value = callback()
        if value:
            if not isinstance(value, str):
                raise TypeError("CANN receipt ABI provider must return header text")
            values.append(value)
    if not values:
        return ""
    if len(set(values)) != 1:
        raise RuntimeError("multiple incompatible CANN receipt ABI providers")
    return values[0]
'''
    path.write_text(text)


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve()
    if root == Path('/workspace/FlagTree').resolve():
        raise RuntimeError('refusing to patch the user main checkout')
    driver = root / 'third_party/ascend/backend/driver.py'
    actual = hashlib.sha256(driver.read_bytes()).hexdigest()
    expected = sys.argv[2]
    if actual != expected:
        raise RuntimeError(
            'actual driver differs from reviewed pinned source; inspect before applying'
        )
    patch_driver(driver)
    patch_shim(root / 'python/flagtree/_flagprism.py')
