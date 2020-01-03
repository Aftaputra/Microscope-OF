def get_docstring(obj):
    ds = obj.__doc__
    if ds:
        return ds.strip()
    else:
        return ""


def get_summary(obj):
    return get_docstring(obj).partition("\n")[0].strip()
