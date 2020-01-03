from flask.views import MethodView


class Resource(MethodView):
    """Currently identical to MethodView
    """

    endpoint = None
    methods = ["get", "post", "put", "delete"]

    def __init__(self, *args, **kwargs):
        MethodView.__init__(self, *args, **kwargs)

    def doc(self):
        docs = {"operations": {}}
        if hasattr(self, "__apispec__"):
            docs.update(self.__apispec__)

        for meth in Resource.methods:
            if hasattr(self, meth) and hasattr(getattr(self, meth), "__apispec__"):
                docs["operations"][meth] = {}
                docs["operations"][meth] = getattr(self, meth).__apispec__
        return docs
