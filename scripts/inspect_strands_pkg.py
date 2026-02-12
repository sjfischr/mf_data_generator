import pkgutil

matches = [m.name for m in pkgutil.iter_modules() if 'strands' in m.name.lower() or 'calculator' in m.name.lower()]
print(matches)
