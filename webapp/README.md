# OpenFlexure Microscope JS Client

## Key info

* Vue.js web application providing a graphical interface for the OFM
* Once built, will be served by the API server from the host root on port 5000

* See [openflexure-microscope-server/README.md](https://gitlab.com/openflexure/openflexure-microscope-server/-/blob/master/README.md) for details on local installation and building

# Developer guidelines

## Creating releases

* JS client is coupled to the API, and is built and distributed with the server.
* See [openflexure-microscope-server/README.md](https://gitlab.com/openflexure/openflexure-microscope-server/-/blob/master/README.md) for details on creating new releases

## Installing

* Install Node.js (and npm)
* Install dependencies with `npm install`
* Node v18 changes SSL, and so you need a legacy version for compatibility:
    * On Windows:  `$env:NODE_OPTIONS = "--openssl-legacy-provider"`
    * On Linux/MacOS `export NODE_OPTIONS=--openssl-legacy-provider`
* Build the static web app with `npm run build`

# Developing

When developing it is useful to use the development server so Vue changes happen instantly without the need to rebuild. To start the development server run:

    npm run serve

You access the development server on a different port (it's printed on the command line when you run the above command).  This means that when the webapp starts up you will need to tell it where the microscope server is, using the "override API origin" field in the page that pops up.  If you are running a test server on your computer, this is most likely `http://localhost:5000/`.

## VS Code and ESLint

To prevent the editor from interfering with ESLint, add to your project `settings.json`:

```json
{
    "editor.tabSize": 2,
    "cSpell.enabled": false,
    "eslint.validate": ["vue","javascript", "javascriptreact"],
    "editor.formatOnSave": false,
    "vetur.validation.template": false,
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": true
    }
}
```
