import os
import sys 

from importlib.util import module_from_spec, spec_from_file_location


# CPYST: You can hit this function from the test. E.g.,:
#
#   # See the first `migrate-hoth test` call from this test:
#   pytest tests/versioning/test_shell.py::TestShellDatabase::test_command_test
#
#   # You can also run this (and probably others):
#   pytest tests/versioning/test_api.py::TestSchemaAPI::test_workflow

def import_path(fullpath):
    """ Import a file with full path specification. Allows one to
        import from anywhere, something __import__ does not do.
    """
    module_name = os.path.splitext(os.path.basename(fullpath))[0]
    # 2023-12-15: This function used 'machinery' previously:
    #     from importlib import machinery
    #     return machinery.SourceFileLoader(name, fullpath).load_module(name)
    # But 'load_module' is deprecated, and emits warning saying so.
    # - This alternative code achieves same result, but also uses load_module:
    #     module_spec = spec_from_file_location(module_name, fullpath)
    #     the_module = module_spec.loader.load_module(module_name)
    # - Fortunately, there's a recipe in the docs how to do this properly,
    #   if you scroll down all the way:
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly

    module_spec = spec_from_file_location(module_name, fullpath)

    # This create a bare module object, or something, it's not the real thing yet.
    the_module = module_from_spec(module_spec)

    # Register the module.
    sys.modules[module_name] = the_module

    # Now hydrate the module, so it's what you'd get on a normal 'import',
    # or what you used to get from 'load_module'.
    module_spec.loader.exec_module(the_module)

    return the_module
