# WebApp Development

## Key info

* Vue.js web application providing a graphical interface for the Openflexure Microscope.
* Once built, will be served by the API server from the host root on port 5000
* JS client is coupled to the API, and is built and distributed with the server.


## Installing

_Note: If you are using a Windows OS, the following commands must be executed in a Powershell terminal._

* [Get Node.js using the official installation scripts for your operating system.](https://nodejs.org/en/download/current)
* Recommended configuration: "Get Node.js v26, for Mac/Linux, using nvm, with npm"
* Using NVM (node-version-manager)
    * To install Node.js v26 run:
        `nvm install 26`
    * To set the Node.js to version 26:
        `nvm use 26`
* Configuration for Windows OS if nvm can't be installed in your system: "Get Node.js v26, for Windows, using Chocolatey, with npm".
* Navigate into the webapp directory with `cd webapp`
* Install dependencies with `npm install`
* Build the static web app with `npm run build`

## Live Server

When developing it is useful to use the development server so Vue changes happen instantly without the need to rebuild. To start the development server run:

    npm run serve

The development server is accessed on a different port from the microscope API. When Vite starts, it creates a proxy that proxies all routes starting with `/api` to `http://localhost:5000/api`. This is useful when using either the simulation server or when developing directly on a microscope.

If developing the webapp on a different computer you can run:

    npm run serve:microscope

This will proxy all routes starting with `/api` to `http://microscope.local:5000/api`.

If your microscope hostname is not `microscope`, you can use local environment files to override this route. Create the file `.env.local` within the `/webapp/` directory, and in that file add the line

    VITE_MICROSCOPE_HOST=http://myhostname.local:5000

(changing `myhostname` to the correct host name.)

**Note:** If you have performance issues with lag, this can be caused by mDNS speed for your setup. To avoid mDNS, overload `VITE_MICROSCOPE_HOST` with the IP address of your microscope, rather than the host name.

# Javascript: Formatting and linting

To enforce code style we and quality we use ESLint and Prettier. Both can be run together with the same command.

- To check the for errors and warnings run `npm run lint`
- To automatically fix errors and warnings run `npm run lint:fix`

