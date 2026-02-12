import inspect
from strands import tools

print('tools module:', tools)
public = [n for n in dir(tools) if not n.startswith('_')]
print('public names:', public[:200])

for name in public:
    try:
        obj = getattr(tools, name)
        if inspect.ismodule(obj):
            sub_public = [n for n in dir(obj) if not n.startswith('_')]
            if 'calculator' in name.lower() or any('calculator' in s.lower() for s in sub_public):
                print('module', name, '->', sub_public[:80])
    except Exception as exc:
        print('err', name, exc)
