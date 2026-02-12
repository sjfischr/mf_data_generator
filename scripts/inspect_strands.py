import importlib
import pkgutil

mods = [m.name for m in pkgutil.iter_modules() if 'strand' in m.name]
print(mods)
for name in mods:
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, '__file__', None))
        public = [a for a in dir(mod) if not a.startswith('_')]
        print(public[:50])
    except Exception as exc:
        print(name, 'ERR', exc)
