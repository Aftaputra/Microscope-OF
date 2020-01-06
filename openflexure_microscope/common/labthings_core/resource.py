class BaseResource:
    """
    A LabThing Resource class should, regardless of the underlying framework, make use of
    functions get(), put(), post(), and delete() corresponding to HTTP methods.

    These functions will allow for automated documentation generation
    """

    methods = ["get", "post", "put", "delete"]

    def doc(self):
        docs = {"operations": {}}
        if hasattr(self, "__apispec__"):
            docs.update(self.__apispec__)

        for meth in BaseResource.methods:
            if hasattr(self, meth) and hasattr(getattr(self, meth), "__apispec__"):
                docs["operations"][meth] = {}
                docs["operations"][meth] = getattr(self, meth).__apispec__
        return docs
