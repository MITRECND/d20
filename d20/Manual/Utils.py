import os
import importlib.machinery
import importlib.util
from typing import List, Dict, Optional, Set


def loadExtras(paths: List[str], loaded: Set, exclude=None,
               exclude_full: Optional[Set] = None) -> None:
    """Initialization method to load extra components

        This function, optionally using external directory paths will
        load python files via importlib triggering the registration of the
        components in those files via the decorators and other functions
    """

    files: Dict[str, Set] = dict()

    # Get all files in these directories
    for path in paths:
        files[path] = set(
            [f for f in os.listdir(path) if os.path.isfile(
                os.path.join(path, f)) and f.endswith(".py")])
        # Remove package file
        try:
            files[path].remove("__init__.py")
        except KeyError:
            pass

    for (path, names) in files.items():
        for name in names:
            fullpath = os.path.join(path, name)
            if exclude is not None and name in exclude:
                continue

            if exclude_full is not None and fullpath in exclude_full:
                continue

            if name.endswith(".py"):
                if name in loaded:
                    continue
                else:
                    loaded.add(name)
                name = name[:-3]

            try:
                spec: Optional[importlib.machinery.ModuleSpec] = \
                    importlib.util.spec_from_file_location(name, fullpath)
                if spec is not None and spec.loader is not None:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)  # type: ignore
                else:
                    raise TypeError

            except (TypeError, AttributeError):
                raise
            except Exception as e:
                raise RuntimeError(e)
