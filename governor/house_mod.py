"""The House forecast's modules, loaded by their path under names of their own (house_<name>), since the repository has
other modules of the same names (polls.py, simulate.py, build_data.py) at its root and in senate/."""
import importlib.util, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    key = 'house_' + name
    if key in sys.modules: return sys.modules[key]
    house = os.path.join(ROOT, 'house')
    if house not in sys.path: sys.path.append(house)            # what the module imports in turn (wiki_house)
    spec = importlib.util.spec_from_file_location(key, os.path.join(house, name + '.py'))
    m = importlib.util.module_from_spec(spec); sys.modules[key] = m; spec.loader.exec_module(m)
    return m
