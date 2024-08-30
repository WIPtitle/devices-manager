import pkgutil

def discover_all_modules(package):
    modules = []
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not is_pkg:
            modules.append(name)
    return modules