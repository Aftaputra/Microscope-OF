import yaml
with open("./build/swagger.yaml", "r") as f:
    api = yaml.load(f)

for path, methods in api["paths"].items():
    for method, properties in methods.items():
        try:
            for k in ["responses", "description"]:
                current_key = k
                _ = properties[k]
            for code, r in properties["responses"].items():
                current_key = f"responses/{code}/description"
                _ = r["description"]
        except KeyError as e:
            print(f"❌ {method} {path} has a problem: {e} from {current_key}")
