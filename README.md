# OpenFlexure Microscope JS Client
[![pipeline status](https://gitlab.com/openflexure/openflexure-microscope-jsclient/badges/master/pipeline.svg?style=flat-square)](https://gitlab.com/openflexure/openflexure-microscope-jsclient/commits/master)

A user client for the OpenFlexure Microscope, written in Vue.js.

## Install

A general guide on setting up your microscope, including OpenFlexure eV, can be found [here on our website](https://www.openflexure.org/projects/microscope/).

## Develop
* Clone the repo, and run `npm install`
* Scripts to build, and package Electron apps, are included in `package.json`

## Builds and deployment
* Binaries will be built for testing on merge requests, and manual CI triggers
    * These builds expire after a week, and are intended for testing only.

* Binaries will be built **and deployed** when a merge into `stable` completes.
    * These binaries will expire on GitLab after a week, but will be permanantly
    deployed to http://build.openflexure.org/openflexure-ev

## Developer notes

### VS Code and ESLint

To prevent the editor from interfering with ESLint, add to your project `settings.json `:

```
{
    "editor.tabSize": 2,
    "cSpell.enabled": false,
    "eslint.validate": [{
            "language": "vue",
            "autoFix": true
        },
        {
            "language": "javascript",
            "autoFix": true
        },
        {
            "language": "javascriptreact",
            "autoFix": true
        }
    ],
    "eslint.autoFixOnSave": true,
    "editor.formatOnSave": false,
    "vetur.validation.template": false
}
```