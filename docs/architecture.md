# Architecture

AlgAlpaca has a React interface, a local FastAPI boundary, and a Python inference and execution pipeline.

```text
problem → frozen prompt → local model generation → code extraction
        → syntax and policy checks → restricted subprocess → displayed result
```

The web service validates the private adapter before loading and loads the model only when generation is requested. Code extraction accepts the established response formats without repair. The execution policy checks the syntax tree for disallowed imports, calls, and constructs before starting a resource-limited subprocess. Standard output is bounded and normalized for presentation; errors are sanitized before reaching the browser.

These controls are intended for a single-user local application. They are not a hardened isolation boundary for untrusted public users.
