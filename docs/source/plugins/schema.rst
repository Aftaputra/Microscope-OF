Adding a GUI
=====================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Components
----------

.. list-table:: Summary of form components
    :widths: 10 10 40 20
    :header-rows: 1
    :stub-columns: 1

    * - Name
      - Data type
      - Properties
      - Example
    * - checkList
      - [str, str,...]
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** ([str, str,...]) List of selected options
      
        **options** ([str, str,...]) List of all options
        
      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/checkList.png 
    * - htmlBlock
      - N/A
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **content** (str) HTML string to be rendered

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/htmlBlock.png 
    * - keyvalList
      - dict
      - **name** (str) Unique name of the component

        **value** (dict) Dictionary of key-value pairs

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/keyvalList.png 
    * - labelInput
      - str
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** (str) Value of the editable label text

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/labelInput.png 
    * - numberInput
      - int
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** (int) Value of the input

        **placeholder** (int) Placeholder value

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/numberInput.png 
    * - radioList
      - String
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** (str) Currently selected option
      
        **options** ([str, str,...]) List of all options

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/radioList.png 
    * - selectList
      - str
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** (str) Currently selected option
      
        **options** ([str, str,...]) List of all options

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/selectList.png 
    * - tagList
      - [str, str,...]
      - **name** (str) Unique name of the component

        **value** ([str, str,...]) List of tag strings

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/tagList.png 
    * - textInput
      - str
      - **name** (str) Unique name of the component

        **label** (str) Friendly label for the component

        **value** (int) Value of the input

        **placeholder** (str) Placeholder value

      - .. figure:: https://openflexure.gitlab.io/assets/plugin-form-components/textInput.png 