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

The development server is accessed on a different port from the microscope API. When VITE starts it creates a proxy that proxies all routes starting with `/api` to `http://localhost:5000/api`. This is useful when using either the simulation server or when developing directly on a microscope.

If developing on a different computer you can run:

    npm run serve:microscope

This will proxy all routes starting with `/api` to `http://microscope.local:5000/api`.

If your microscope hostname is not `microscope` you can use local environament files to override this route. Create the file `.env.local` within the `/webapp/` directory within that file add the line

    VITE_MICROSCPOPE_HOST=http://myhostname.local:5000

(changing `myhostname` to the correct host name.)

# Javascript: Formatting and linting

To enforce code style we and quality we use ESLint and Prettier. Both can be run together with the same command.

- To check the for errors and warnings run `npm run lint`
- To automatically fix errors and warnings run `npm run lint:fix`

