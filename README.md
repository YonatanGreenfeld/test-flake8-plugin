flake8-require-permissions
==========================
This is a flake8 plugin that checks for the existence of the `@require_permissions` decorator on
all HTTP Lambda functions.

### Serverless File

The plugin attempts to discover a serverless file from the `cwd` and above.
Running the plugin from different directories may result in different results.
