def get_docstring(obj):
    ds = obj.__doc__
    if ds:
        return ds.strip()
    else:
        return ""
