# WebApp Development

## Key info

* Vue.js web application providing a graphical interface for the Openflexure Microscope.
* Once built, will be served by the API server from the host root on port 5000
* JS client is coupled to the API, and is built and distributed with the server.


## Installing

_Note: If you are using a Windows OS, the following commands must be executed in a Powershell terminal._

* Install Node.js v18 (and npm)
* Navigate into the webapp directory with `cd webapp`
* Install dependencies with `npm install`
* Build the static web app with `npm run build`

## Live Server

When developing it is useful to use the development server so Vue changes happen instantly without the need to rebuild. To start the development server run:

    npm run serve

The development server is accessed on a different port from the microscope API. The port to access the development server is printed on the command line when you run the above command.

When the development webapp starts it cannot locate the microscope API as this is served by the microscope on port 5000. Instead it will present you with a page giving you the option to "override API origin". If you are running a development server on your computer, you should enter `http://localhost:5000/`.

# Javascript: Formatting and linting

To enforce code style we and quality we use ESLint and Prettier. Both can be run together with the same command.

- To check the for errors and warnings run `npm run lint`
- To automatically fix errors and warnings run `npm run lint:fix`

