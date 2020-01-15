HTTP API
========

Live documentation
------------------

Full, interactive Swagger documentation for your microscopes web API is available from the microscope itself. From any browser, go to ``http://{your microscope IP address}/api/v2/swagger-ui``.

Default views
-------------
.. autoflask:: openflexure_microscope.api.app:app
   :undoc-endpoints: index
   :undoc-static:
   :endpoints:
   :order: path
