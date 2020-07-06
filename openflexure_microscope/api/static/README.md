# OpenFlexure Microscope JS Client

## Developer notes

### VS Code and ESLint

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