# Architecture

AlgAlpaca has a React interface, a local FastAPI boundary, and a Python inference and execution pipeline.

```text
problem → frozen prompt → local model generation → code extraction
        → syntax and policy checks → restricted subprocess → displayed result
```

The web service validates the private adapter before loading and loads the model only when generation is requested. Code extraction accepts the established response formats without repair. The execution policy checks the syntax tree for disallowed imports, calls, and constructs before starting a resource-limited subprocess. Standard output is bounded and normalized for presentation; errors are sanitized before reaching the browser.

These controls are intended for a single-user local application. They are not a hardened isolation boundary for untrusted public users.

The repository contains the application and compact evaluation artifacts, not adapter weights. `.algalpaca-adapter-path` is a one-line ignored local file that tells the app where to find the external adapter. The current runtime accepts only the v2 checkpoint identity: a directory that does not match the expected sizes, hashes, and PEFT configuration is rejected.

V2 commonly returns complete raw Python. The extractor accepts that form only when the entire nonempty response parses as one Python module and contains no wrapper markup or surrounding prose. It does not repair code, insert imports or output statements, or choose among competing programs.
