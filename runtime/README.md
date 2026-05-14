# Runtime

This directory is reserved for generated local runtime files.

The portable installer creates `runtime/.venv` here. The generated environment is machine-specific and ignored by git, so the project can be copied to another computer and installed again without carrying local paths.
