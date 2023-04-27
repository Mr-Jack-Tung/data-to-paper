import builtins
import traceback
from contextlib import contextmanager
from typing import List, Tuple, Any

from scientistgpt.run_gpt_code.exceptions import CodeUsesForbiddenFunctions, \
    CodeWriteForbiddenFile, CodeReadForbiddenFile, CodeImportForbiddenModule


@contextmanager
def prevent_file_open(allowed_read_files: List[str] = None, allowed_write_files: List[str] = None):
    """
    Context manager for restricting the code from opening un-allowed files.

    allowed_read_files: list of files that the code is allowed to read from. If None, all files are allowed.
    allowed_write_files: list of files that the code is allowed to write to. If None, all files are allowed.
    """

    original_open = builtins.open

    def open_wrapper(*args, **kwargs):
        file_name = args[0] if len(args) > 0 else kwargs.get('file', None)
        open_mode = args[1] if len(args) > 1 else kwargs.get('mode', 'r')
        is_opening_for_writing = open_mode in ['w', 'a', 'x']
        if is_opening_for_writing and allowed_write_files is not None and file_name not in allowed_write_files:
            raise CodeWriteForbiddenFile(file=file_name)
        if not is_opening_for_writing and allowed_read_files is not None and file_name not in allowed_read_files:
            raise CodeReadForbiddenFile(file=file_name)
        return original_open(*args, **kwargs)

    builtins.open = open_wrapper
    try:
        yield
    finally:
        builtins.open = original_open


@contextmanager
def prevent_calling(modules_and_functions: List[Tuple[Any, str]] = None):
    """
    Context manager for catching when the code tries to use certain forbidden functions.

    modules_and_functions: list of tuples of (module, function_name) that the code is not allowed to call.
    """
    modules_and_functions = modules_and_functions or []

    def get_upon_called(func_name, original_func):
        from scientistgpt.run_gpt_code.dynamic_code import module_filename

        def upon_called(*args, **kwargs):
            # We check that the function was called from the module we are running
            # (functions like print are also called from pytest)
            frame = traceback.extract_stack()[-2]
            if frame.filename.endswith(module_filename):
                raise CodeUsesForbiddenFunctions(func_name)
            return original_func(*args, **kwargs)
        return upon_called

    original_functions = []

    for module, function_name in modules_and_functions:
        original_function = getattr(module, function_name)
        original_functions.append(original_function)
        setattr(module, function_name, get_upon_called(function_name, original_function))

    try:
        yield
    finally:
        # we restore the original functions
        for module, function_name in modules_and_functions:
            setattr(module, function_name, original_functions.pop(0))


class PreventImport:
    def __init__(self, modules):
        from scientistgpt.run_gpt_code.dynamic_code import module_filename
        self.modules = modules
        self.module_filename = module_filename

    def __enter__(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self.custom_import
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        builtins.__import__ = self.original_import

    def custom_import(self, name, *args, **kwargs):
        if any(name.startswith(module + '.') for module in self.modules) or name in self.modules:
            frame = traceback.extract_stack()[-2]
            if frame.filename.endswith(self.module_filename):
                raise CodeImportForbiddenModule(module=name)
        return self.original_import(name, *args, **kwargs)