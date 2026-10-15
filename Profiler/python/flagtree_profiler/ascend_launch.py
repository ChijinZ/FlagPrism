"""Authoritative C++ capsule ABI for the generated Ascend launch worker."""
from pathlib import Path


def get_launch_receipt_abi():
    """Read the installed header, or its canonical source for editable builds.

    The generated launcher embeds these exact bytes in its source/cache key.
    This reads no SDK, starts no collector and imports no native module.
    """
    package = Path(__file__).resolve().parent
    packaged = package / '_cann_launch_receipt.h'
    source = package.parents[
        1] / 'csrc/include/Profiler/Vendor/CannLaunchReceipt.h'
    path = packaged if packaged.is_file() else source
    if not path.is_file():
        raise RuntimeError(
            'CANN receipt ABI header missing from the profiler installation; rebuild/install with its packaged _cann_launch_receipt.h'
        )
    text = path.read_text(encoding='utf-8')
    if 'struct CannLaunchWorkerRecordV1' not in text or 'struct CannLaunchReceiptSinkV1' not in text:
        raise RuntimeError(
            'CANN receipt ABI header does not contain the supported versioned declarations'
        )
    return text
